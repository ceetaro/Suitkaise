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
    - Deserializing the Skprocess object
    - Running the lifecycle (prerun → run → postrun)
    - Handling timeouts
    - Managing lives/retry on errors
    - Timing all lifecycle methods
    - Sending results back to parent
    
    Args:
        serialized_process: Skprocess object serialized with cucumber
        stop_event: Event to check for stop signal from parent
        result_queue: Queue to send results/errors back to parent
        original_state: Original serialized state for retries (lives system)
        tell_queue: Queue for receiving data from parent (parent calls tell())
        listen_queue: Queue for sending data to parent (parent calls listen())
    """
    import traceback
    import sys
    
    try:
        # run inner engine so outer can report fatal errors
        _engine_main_inner(serialized_process, stop_event, result_queue, original_state,
                          tell_queue, listen_queue)
    except Exception as e:
        # DEBUG: Catch ANY uncaught exception and report it
        print(f"\n[ENGINE ERROR] Uncaught exception in subprocess:", file=sys.stderr)
        print(f"  Type: {type(e).__name__}", file=sys.stderr)
        print(f"  Message: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        
        # try to send error payload back to parent
        try:
            from suitkaise import cucumber
            result_queue.put({
                "type": "error", 
                "data": cucumber.serialize(e),
                "timers": None
            })
        except Exception as send_err:
            print(f"[ENGINE ERROR] Failed to send error to parent: {send_err}", file=sys.stderr)
    
    # cancel feeder threads on tell/listen queues which may not be consumed
    # result queue is NOT canceled - parent must call result() to get data
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
    from suitkaise import cucumber, timing
    from .errors import (
        PreRunError, RunError, PostRunError, 
        OnFinishError, ResultError, ProcessTimeoutError
    )
    from .timeout import run_with_timeout
    from .timers import ProcessTimers
    
    # deserialize the process object from serialized state
    process = cucumber.deserialize(serialized_process)
    
    # ensure timers exist for lifecycle timing
    if process.timers is None:
        process.timers = ProcessTimers()
    
    # track lives for retry system
    lives_remaining = process.process_config.lives
    
    # store stop_event reference so lifecycle methods can check or stop
    process._stop_event = stop_event
    
    # set up communication queues for tell/listen

    # NOTE: Queues are SWAPPED in subprocess for symmetric tell/listen API
    #  don't think about it too much, just know that tell() and listen() always make sense
    #  no matter if it is the parent or target process

    process._tell_queue = listen_queue  # subprocess tell() → parent listen()
    process._listen_queue = tell_queue  # parent tell() → subprocess listen()
    
    # record start time for join_in limit
    process._start_time = timing.time()
    
    while lives_remaining > 0:
        try:
            # main execution loop for lifecycle sections
            while _should_continue(process, stop_event):
                
                # PRE RUN
                _run_section_timed(
                    process, 
                    '__prerun__', 
                    'prerun',
                    PreRunError,
                    stop_event
                )
                
                if stop_event.is_set():
                    break
                
                # RUN
                _run_section_timed(
                    process,
                    '__run__',
                    'run', 
                    RunError,
                    stop_event
                )
                
                if stop_event.is_set():
                    break
                
                # POST RUN
                _run_section_timed(
                    process,
                    '__postrun__',
                    'postrun',
                    PostRunError,
                    stop_event
                )
                
                # increment run counter after a full iteration
                process._current_run += 1
                
                # update full_run timer after successful iteration
                if process.timers is not None:
                    process.timers._update_full_run()
            
            # normal exit path runs finish sequence and sends result
            _run_finish_sequence(process, stop_event, result_queue)
            return  # success
            
        except (PreRunError, RunError, PostRunError, ProcessTimeoutError) as e:
            # error in run lifecycle checks lives for retry
            lives_remaining -= 1
            
            if lives_remaining > 0:
                # retry keeps user state and run counter for next attempt
                # failed timings are already discarded via timer.discard
                process.process_config.lives = lives_remaining
                process._stop_event = stop_event
                continue
            else:
                # no lives left so send error back
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
        process: The Skprocess instance
        method_name: Name of the method to call (e.g., '__run__')
        timer_name: Name of the timer slot (e.g., 'run')
        error_class: Error class to wrap exceptions in
        stop_event: Stop event to check
    """
    from .timeout import run_with_timeout
    from .errors import ProcessTimeoutError
    
    # get the actual method and unwrap TimedMethod if needed
    method_attr = getattr(process, method_name)
    if hasattr(method_attr, '_method'):
        # It's a TimedMethod wrapper
        method = method_attr._method
    else:
        method = method_attr
    
    # get timeout for this section
    timeout = getattr(process.process_config.timeouts, timer_name, None)
    
    # get or create timer for this section
    timer = process.timers._ensure_timer(timer_name)
    
    # time the section and run with timeout guard
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
        timer.discard()  # don't record failed timing
        raise
    except Exception as e:
        timer.discard()  # don't record failed timing
        raise error_class(process._current_run, e) from e


def _should_continue(process: Any, stop_event: "Event") -> bool:
    """
    Check if the run loop should continue.
    
    Returns False if:
    - Stop event is set
    - runs limit reached
    - join_in time limit reached
    """
    from suitkaise import timing
    
    # check stop signal
    if stop_event.is_set():
        return False
    
    # check run count limit
    if process.process_config.runs is not None:
        if process._current_run >= process.process_config.runs:
            return False
    
    # check time limit
    if process.process_config.join_in is not None:
        elapsed = timing.elapsed(process._start_time)
        if elapsed >= process.process_config.join_in:
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
    from suitkaise import cucumber
    from .errors import OnFinishError, ResultError, ProcessTimeoutError
    from .timeout import run_with_timeout
    
    # ON FINISH
    method_attr = getattr(process, '__onfinish__')
    if hasattr(method_attr, '_method'):
        method = method_attr._method
    else:
        method = method_attr
    
    timeout = process.process_config.timeouts.onfinish
    
    # time onfinish if user defined it
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
            # onfinish timeout is fatal so send error
            _send_error(process, e, result_queue)
            return
        except Exception as e:
            error = OnFinishError(process._current_run, e)
            _send_error(process, error, result_queue)
            return
    finally:
        if process.timers is not None:
            timer.stop()
    
    # RESULT
    result_method_attr = getattr(process, '__result__')
    if hasattr(result_method_attr, '_method'):
        result_method = result_method_attr._method
    else:
        result_method = result_method_attr
    
    result_timeout = process.process_config.timeouts.result
    
    # time result if user defined it
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
    
    # send successful result with timers
    try:
        serialized_result = cucumber.serialize(result)
        serialized_timers = cucumber.serialize(process.timers) if process.timers else None
        result_queue.put({
            "type": "result", 
            "data": serialized_result,
            "timers": serialized_timers
        })
    except Exception as e:
        # try to send the error
        _send_error(process, e, result_queue)


def _send_error(
    process: Any,
    error: BaseException,
    result_queue: "Queue[Any]"
) -> None:
    """
    Call __error__ and send error result back to parent.
    """
    from suitkaise import cucumber
    from .errors import ErrorHandlerError
    from .timeout import run_with_timeout
    
    # set error on process for __error__ to access
    process.error = error
    
    # get the __error__ method
    error_method_attr = getattr(process, '__error__')
    if hasattr(error_method_attr, '_method'):
        error_method = error_method_attr._method
    else:
        error_method = error_method_attr
    
    error_timeout = process.process_config.timeouts.error
    
    # time __error__ if user defined it
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
            # if __error__ itself fails just send the original error
            error_result = error
    finally:
        if process.timers is not None:
            error_timer.stop()
    
    # serialize and send with timers
    serialized_error = cucumber.serialize(error_result)
    serialized_timers = cucumber.serialize(process.timers) if process.timers else None
    result_queue.put({
        "type": "error", 
        "data": serialized_error,
        "timers": serialized_timers
    })
