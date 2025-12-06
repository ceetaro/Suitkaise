"""
Engine that runs in the subprocess.

Handles the actual loop execution, timeout enforcement, error handling,
lives/retry system, and communication back to the parent process.
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event
    from multiprocessing import Queue


def _engine_main(
    serialized_process: bytes,
    stop_event: "Event",
    result_queue: "Queue[Any]",
    original_state: bytes
) -> None:
    """
    Main entry point for the subprocess engine.
    
    This function runs in the child process and orchestrates:
    - Deserializing the Process object
    - Running the lifecycle loop (preloop → loop → postloop)
    - Handling timeouts
    - Managing lives/retry on errors
    - Sending results back to parent
    
    Args:
        serialized_process: Process object serialized with cerial
        stop_event: Event to check for stop signal from parent
        result_queue: Queue to send results/errors back to parent
        original_state: Original serialized state for retries (lives system)
    """
    import traceback
    import sys
    
    try:
        _engine_main_inner(serialized_process, stop_event, result_queue, original_state)
    except Exception as e:
        # DEBUG: Catch ANY uncaught exception and report it
        print(f"\n[ENGINE ERROR] Uncaught exception in subprocess:", file=sys.stderr)
        print(f"  Type: {type(e).__name__}", file=sys.stderr)
        print(f"  Message: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        
        # Try to send error back through queue
        try:
            from suitkaise import cerial
            result_queue.put({"type": "error", "data": cerial.serialize(e)})
        except Exception as send_err:
            print(f"[ENGINE ERROR] Failed to send error to parent: {send_err}", file=sys.stderr)


def _engine_main_inner(
    serialized_process: bytes,
    stop_event: "Event",
    result_queue: "Queue[Any]",
    original_state: bytes
) -> None:
    """Inner engine implementation."""
    from suitkaise import cerial, sktime
    from .errors import (
        PreloopError, MainLoopError, PostLoopError, 
        OnFinishError, ResultError, TimeoutError
    )
    from .timeout import run_with_timeout
    
    # Deserialize the process
    process = cerial.deserialize(serialized_process)
    
    # Track lives for retry system
    lives_remaining = process.config.lives
    
    # Store reference to stop_event on process so lifecycle methods can use stop()
    process._stop_event = stop_event
    
    # Record start time for join_in limit
    process._start_time = sktime.now()
    
    while lives_remaining > 0:
        try:
            # Main execution loop
            while _should_continue(process, stop_event):
                
                # === PRELOOP ===
                try:
                    run_with_timeout(
                        process.__preloop__,
                        process.config.timeouts.preloop,
                        '__preloop__',
                        process._current_lap
                    )
                except TimeoutError:
                    raise
                except Exception as e:
                    raise PreloopError(process._current_lap, e) from e
                
                if stop_event.is_set():
                    break
                
                # === LOOP ===
                try:
                    run_with_timeout(
                        process.__loop__,
                        process.config.timeouts.loop,
                        '__loop__',
                        process._current_lap
                    )
                except TimeoutError:
                    raise
                except Exception as e:
                    raise MainLoopError(process._current_lap, e) from e
                
                if stop_event.is_set():
                    break
                
                # === POSTLOOP ===
                try:
                    run_with_timeout(
                        process.__postloop__,
                        process.config.timeouts.postloop,
                        '__postloop__',
                        process._current_lap
                    )
                except TimeoutError:
                    raise
                except Exception as e:
                    raise PostLoopError(process._current_lap, e) from e
                
                # Increment lap counter
                process._current_lap += 1
                
                # Update full_loop timer if timers exist
                if process.timers is not None:
                    process.timers._update_full_loop()
            
            # === Normal exit - run finish sequence ===
            _run_finish_sequence(process, stop_event, result_queue)
            return  # Success!
            
        except (PreloopError, MainLoopError, PostLoopError, TimeoutError) as e:
            # Error in loop - check if we have lives to retry
            lives_remaining -= 1
            
            if lives_remaining > 0:
                # Retry with fresh state
                process = cerial.deserialize(original_state)
                process.config.lives = lives_remaining
                process._stop_event = stop_event
                process._start_time = sktime.now()
                process._current_lap = 0
                continue
            else:
                # No lives left - send error back
                _send_error(process, e, result_queue)
                return


def _should_continue(process: Any, stop_event: "Event") -> bool:
    """
    Check if the loop should continue.
    
    Returns False if:
    - Stop event is set
    - num_loops limit reached
    - join_in time limit reached
    """
    from suitkaise import sktime
    
    # Check stop signal
    if stop_event.is_set():
        return False
    
    # Check loop count limit
    if process.config.num_loops is not None:
        if process._current_lap >= process.config.num_loops:
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
    from .errors import OnFinishError, ResultError, TimeoutError
    from .timeout import run_with_timeout
    
    # === ONFINISH ===
    try:
        run_with_timeout(
            process.__onfinish__,
            process.config.timeouts.onfinish,
            '__onfinish__',
            process._current_lap
        )
    except TimeoutError as e:
        # Onfinish timeout is fatal - send error
        _send_error(process, e, result_queue)
        return
    except Exception as e:
        error = OnFinishError(process._current_lap, e)
        _send_error(process, error, result_queue)
        return
    
    # === RESULT ===
    try:
        result = process.__result__()
    except Exception as e:
        error = ResultError(process._current_lap, e)
        _send_error(process, error, result_queue)
        return
    
    # Send successful result
    try:
        serialized_result = cerial.serialize(result)
        result_queue.put({"type": "result", "data": serialized_result})
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
    
    # Set error on process for __error__ to access
    process.error = error
    
    # Call __error__ handler
    try:
        error_result = process.__error__()
    except Exception:
        # If __error__ itself fails, just send the original error
        error_result = error
    
    # Serialize and send
    serialized_error = cerial.serialize(error_result)
    result_queue.put({"type": "error", "data": serialized_error})

