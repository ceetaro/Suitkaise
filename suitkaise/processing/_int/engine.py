"""
Engine that runs in the subprocess.

Handles the actual execution, timeout enforcement, error handling,
lives/retry system, timing, and communication back to the parent process.
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event
    from multiprocessing import Queue


def _engine_main(
    serialized_process: bytes,
    stop_event: "Event",
    result_queue: "Queue[Any]",
    original_state: bytes,
    tell_queue: "Queue[Any]" = None,
    listen_queue: "Queue[Any]" = None
) -> None:
    """
    Main entry point for the subprocess engine.
    
    This function runs in the child process and orchestrates:
    - Deserializing the Process object
    - Running the lifecycle (prerun → run → postrun)
    - Handling timeouts
    - Managing lives/retry on errors
    - Timing all lifecycle methods
    - Sending results back to parent
    
    Args:
        serialized_process: Process object serialized with cerial
        stop_event: Event to check for stop signal from parent
        result_queue: Queue to send results/errors back to parent
        original_state: Original serialized state for retries (lives system)
        tell_queue: Queue for receiving data from parent (parent calls tell())
        listen_queue: Queue for sending data to parent (parent calls listen())
    """
    import traceback
    import sys
    
    try:
        _engine_main_inner(serialized_process, stop_event, result_queue, original_state,
                          tell_queue, listen_queue)
    except Exception as e:
        # DEBUG: Catch ANY uncaught exception and report it
        print(f"\n[ENGINE ERROR] Uncaught exception in subprocess:", file=sys.stderr)
        print(f"  Type: {type(e).__name__}", file=sys.stderr)
        print(f"  Message: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        
        # Try to send error back through queue
        try:
            from suitkaise import cerial
            result_queue.put({
                "type": "error", 
                "data": cerial.serialize(e),
                "timers": None
            })
        except Exception as send_err:
            print(f"[ENGINE ERROR] Failed to send error to parent: {send_err}", file=sys.stderr)
    
    # Cancel feeder threads on tell/listen queues which may not be consumed
    # Result queue is NOT canceled - parent must call result() to get data
    for q in [tell_queue, listen_queue]:
        if q is not None:
            try:
                q.cancel_join_thread()
            except Exception:
                pass


def _engine_main_inner(
    serialized_process: bytes,
    stop_event: "Event",
    result_queue: "Queue[Any]",
    original_state: bytes,
    tell_queue: "Queue[Any]" = None,
    listen_queue: "Queue[Any]" = None
) -> None:
    """Inner engine implementation."""
    from suitkaise import cerial, sktime
    from .errors import (
        PreRunError, RunError, PostRunError, 
        OnFinishError, ResultError, ProcessTimeoutError
    )
    from .timeout import run_with_timeout
    from .timers import ProcessTimers
    
    # Deserialize the process
    process = cerial.deserialize(serialized_process)
    
    # Ensure timers exist
    if process.timers is None:
        process.timers = ProcessTimers()
    
    # Track lives for retry system
    lives_remaining = process.config.lives
    
    # Store reference to stop_event on process so lifecycle methods can use stop()
    process._stop_event = stop_event
    
    # Set up communication queues for tell/listen
    # IMPORTANT: Queues are SWAPPED in subprocess for symmetric tell/listen API
    # - Parent's tell() puts in tell_queue → subprocess's listen() gets from it
    # - Subprocess's tell() puts in listen_queue → parent's listen() gets from it
    process._tell_queue = listen_queue  # subprocess tell() → parent listen()
    process._listen_queue = tell_queue  # parent tell() → subprocess listen()
    
    # Record start time for join_in limit
    process._start_time = sktime.time()
    
    while lives_remaining > 0:
        try:
            # Main execution loop
            while _should_continue(process, stop_event):
                
                # === PRERUN ===
                _run_section_timed(
                    process, 
                    '__prerun__', 
                    'prerun',
                    PreRunError,
                    stop_event
                )
                
                if stop_event.is_set():
                    break
                
                # === RUN ===
                _run_section_timed(
                    process,
                    '__run__',
                    'run', 
                    RunError,
                    stop_event
                )
                
                if stop_event.is_set():
                    break
                
                # === POSTRUN ===
                _run_section_timed(
                    process,
                    '__postrun__',
                    'postrun',
                    PostRunError,
                    stop_event
                )
                
                # Increment run counter
                process._current_run += 1
                
                # Update full_run timer
                if process.timers is not None:
                    process.timers._update_full_run()
            
            # === Normal exit - run finish sequence ===
            _run_finish_sequence(process, stop_event, result_queue)
            return  # Success!
            
        except (PreRunError, RunError, PostRunError, ProcessTimeoutError) as e:
            # Error in run - check if we have lives to retry
            lives_remaining -= 1
            
            if lives_remaining > 0:
                # Retry: keep user state and run counter, retry current iteration
                # Failed timings already discarded via timer.discard()
                process.config.lives = lives_remaining
                process._stop_event = stop_event
                continue
            else:
                # No lives left - send error back
                _send_error(process, e, result_queue)
                return


def _run_section_timed(
    process: Any,
    method_name: str,
    timer_name: str,
    error_class: type,
    stop_event: "Event"
) -> None:
    """
    Run a lifecycle section with timing and error handling.
    
    Args:
        process: The Process instance
        method_name: Name of the method to call (e.g., '__run__')
        timer_name: Name of the timer slot (e.g., 'run')
        error_class: Error class to wrap exceptions in
        stop_event: Stop event to check
    """
    from .timeout import run_with_timeout
    from .errors import ProcessTimeoutError
    
    # Get the actual method (unwrap TimedMethod if needed)
    method_attr = getattr(process, method_name)
    if hasattr(method_attr, '_method'):
        # It's a TimedMethod wrapper
        method = method_attr._method
    else:
        method = method_attr
    
    # Get timeout for this section
    timeout = getattr(process.config.timeouts, timer_name, None)
    
    # Get or create timer
    timer = process.timers._ensure_timer(timer_name)
    
    # Time the section
    timer.start()
    try:
        run_with_timeout(
            method,
            timeout,
            method_name,
            process._current_run
        )
        timer.stop()  # Record successful timing
    except ProcessTimeoutError:
        timer.discard()  # Don't record failed timing
        raise
    except Exception as e:
        timer.discard()  # Don't record failed timing
        raise error_class(process._current_run, e) from e


def _should_continue(process: Any, stop_event: "Event") -> bool:
    """
    Check if the run loop should continue.
    
    Returns False if:
    - Stop event is set
    - runs limit reached
    - join_in time limit reached
    """
    from suitkaise import sktime
    
    # Check stop signal
    if stop_event.is_set():
        return False
    
    # Check run count limit
    if process.config.runs is not None:
        if process._current_run >= process.config.runs:
            return False
    
    # Check time limit
    if process.config.join_in is not None:
        elapsed = sktime.elapsed(process._start_time)
        if elapsed >= process.config.join_in:
            return False
    
    return True


def _run_finish_sequence(
    process: Any,
    stop_event: "Event",
    result_queue: "Queue[Any]"
) -> None:
    """
    Run __onfinish__ and __result__, send result back to parent.
    """
    from suitkaise import cerial
    from .errors import OnFinishError, ResultError, ProcessTimeoutError
    from .timeout import run_with_timeout
    
    # === ONFINISH ===
    method_attr = getattr(process, '__onfinish__')
    if hasattr(method_attr, '_method'):
        method = method_attr._method
    else:
        method = method_attr
    
    timeout = process.config.timeouts.onfinish
    
    # Time onfinish if user defined it
    if process.timers is not None:
        timer = process.timers._ensure_timer('onfinish')
        timer.start()
    
    try:
        try:
            run_with_timeout(
                method,
                timeout,
                '__onfinish__',
                process._current_run
            )
        except ProcessTimeoutError as e:
            # Onfinish timeout is fatal - send error
            _send_error(process, e, result_queue)
            return
        except Exception as e:
            error = OnFinishError(process._current_run, e)
            _send_error(process, error, result_queue)
            return
    finally:
        if process.timers is not None:
            timer.stop()
    
    # === RESULT ===
    result_method_attr = getattr(process, '__result__')
    if hasattr(result_method_attr, '_method'):
        result_method = result_method_attr._method
    else:
        result_method = result_method_attr
    
    result_timeout = process.config.timeouts.result
    
    # Time result if user defined it
    if process.timers is not None:
        result_timer = process.timers._ensure_timer('result')
        result_timer.start()
    
    try:
        try:
            result = run_with_timeout(
                result_method,
                result_timeout,
                '__result__',
                process._current_run
            )
        except ProcessTimeoutError as e:
            _send_error(process, e, result_queue)
            return
        except Exception as e:
            error = ResultError(process._current_run, e)
            _send_error(process, error, result_queue)
            return
    finally:
        if process.timers is not None:
            result_timer.stop()
    
    # Send successful result with timers
    try:
        serialized_result = cerial.serialize(result)
        serialized_timers = cerial.serialize(process.timers) if process.timers else None
        result_queue.put({
            "type": "result", 
            "data": serialized_result,
            "timers": serialized_timers
        })
    except Exception as e:
        # Try to send the error
        _send_error(process, e, result_queue)


def _send_error(
    process: Any,
    error: BaseException,
    result_queue: "Queue[Any]"
) -> None:
    """
    Call __error__ and send error result back to parent.
    """
    from suitkaise import cerial
    from .errors import ErrorError
    from .timeout import run_with_timeout
    
    # Set error on process for __error__ to access
    process.error = error
    
    # Get the __error__ method
    error_method_attr = getattr(process, '__error__')
    if hasattr(error_method_attr, '_method'):
        error_method = error_method_attr._method
    else:
        error_method = error_method_attr
    
    error_timeout = process.config.timeouts.error
    
    # Time __error__ if user defined it
    if process.timers is not None:
        error_timer = process.timers._ensure_timer('error')
        error_timer.start()
    
    try:
        try:
            error_result = run_with_timeout(
                error_method,
                error_timeout,
                '__error__',
                process._current_run
            )
        except Exception:
            # If __error__ itself fails, just send the original error
            error_result = error
    finally:
        if process.timers is not None:
            error_timer.stop()
    
    # Serialize and send with timers
    serialized_error = cerial.serialize(error_result)
    serialized_timers = cerial.serialize(process.timers) if process.timers else None
    result_queue.put({
        "type": "error", 
        "data": serialized_error,
        "timers": serialized_timers
    })
