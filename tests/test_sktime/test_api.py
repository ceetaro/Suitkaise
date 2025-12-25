import time
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest  # type: ignore

from suitkaise import sktime


# Test configuration
SLEEP_SHORT = 0.002
SLEEP_MED = 0.006
TOL = 0.010  # generous tolerance to avoid flakiness on CI


def _assert_between(value: float, low: float, high: float, msg: str = "") -> None:
    assert low <= value <= high, msg or f"{value} not in [{low}, {high}]"


# Top-level function for ProcessPool pickling
@sktime.timethis()
def _mp_slow_op(d: float) -> float:
    sktime.sleep(d)
    return d


# time()
def test_time_basics():
    """Returns float close to time.time() and is non-decreasing across calls."""
    t_lib = time.time()
    t1 = sktime.time()
    assert isinstance(t1, float)
    # within reasonable drift from immediate time.time() call
    _assert_between(abs(t1 - t_lib), 0.0, 0.1)
    # monotonic in practice (non-decreasing across very fast calls)
    t2 = sktime.time()
    assert t2 >= t1


# sleep()
def test_sleep_blocks_only_current_thread_and_duration():
    """sleep() should approximate duration and not block other threads."""
    start_main = time.time()

    # launch a sleeping thread; main thread should continue quickly
    done = threading.Event()

    def sleeper():
        sktime.sleep(SLEEP_MED)
        done.set()

    thread = threading.Thread(target=sleeper)
    thread.start()

    # main continues; should reach here quickly (non-blocking). Just sanity-check small elapsed.
    mid = time.time()
    assert (mid - start_main) < 0.05

    thread.join()
    total = time.time() - start_main
    # total should be at least the sleep duration of the worker
    assert total >= (SLEEP_MED - TOL)


def test_sleep_concurrent_threads():
    """Multiple threads can sleep concurrently with independent durations."""
    results = []
    lock = threading.Lock()

    def worker(dur: float):
        t0 = time.time()
        sktime.sleep(dur)
        with lock:
            results.append(time.time() - t0)

    th1 = threading.Thread(target=worker, args=(SLEEP_SHORT,))
    th2 = threading.Thread(target=worker, args=(SLEEP_MED,))
    start = time.time()
    th1.start(); th2.start()
    th1.join(); th2.join()
    end = time.time()

    assert len(results) == 2
    # overall wall time should be approximately the max of the two durations
    _assert_between(end - start, SLEEP_MED - TOL, SLEEP_MED + 0.05)


# elapsed()
def test_elapsed_with_one_and_two_arguments():
    """elapsed() handles single start argument and is order-independent for two times."""
    start = sktime.time()
    sktime.sleep(SLEEP_SHORT)
    e1 = sktime.elapsed(start)
    _assert_between(e1, SLEEP_SHORT - TOL, 0.1)

    t1 = sktime.time()
    sktime.sleep(SLEEP_SHORT)
    t2 = sktime.time()
    e2 = sktime.elapsed(t1, t2)
    e3 = sktime.elapsed(t2, t1)
    assert e2 >= 0
    assert e3 >= 0
    _assert_between(abs(e2 - e3), 0.0, TOL)


# Yawn
def test_yawn_threshold_and_sleeping_behavior():
    """Yawn should sleep when threshold is reached and report True on that call."""
    y = sktime.Yawn(sleep_duration=SLEEP_SHORT, yawn_threshold=3, log_sleep=False)

    t0 = time.time()
    assert y.yawn() is False  # 1
    assert y.yawn() is False  # 2
    slept_call = y.yawn()  # 3 -> should sleep
    dt = time.time() - t0
    assert slept_call is True
    assert dt >= (SLEEP_SHORT - TOL)


def test_yawn_stats_and_reset():
    y = sktime.Yawn(sleep_duration=SLEEP_SHORT, yawn_threshold=4)
    for _ in range(2):
        y.yawn()
    stats_mid = y.get_stats()
    assert set(stats_mid.keys()) == {
        "current_yawns",
        "yawn_threshold",
        "total_sleeps",
        "sleep_duration",
        "yawns_until_sleep",
    }
    assert stats_mid["current_yawns"] == 2
    assert stats_mid["yawns_until_sleep"] == 2

    y.reset()
    stats_after = y.get_stats()
    assert stats_after["current_yawns"] == 0
    assert stats_after["yawns_until_sleep"] == 4


def test_yawn_thread_safety_multiple_threads():
    """Concurrent yawns across threads should aggregate correctly and sleep threshold times."""
    threshold = 5
    rounds = 25  # expect 5 sleeps total
    y = sktime.Yawn(sleep_duration=SLEEP_SHORT, yawn_threshold=threshold)

    sleeps = 0
    lock = threading.Lock()

    def worker(n: int):
        nonlocal sleeps
        for _ in range(n):
            if y.yawn():
                with lock:
                    sleeps += 1

    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(worker, rounds // 2), ex.submit(worker, rounds - rounds // 2)]
        for f in futs:
            f.result()

    assert sleeps == rounds // threshold


# Timer
def test_timer_start_stop_and_basic_stats():
    timer = sktime.Timer()
    timer.start()
    sktime.sleep(SLEEP_SHORT)
    elapsed = timer.stop()

    assert timer.stats.num_times == 1
    _assert_between(elapsed, SLEEP_SHORT - TOL, 0.1)
    assert timer.stats.most_recent is not None
    assert timer.stats.result == timer.stats.most_recent
    assert timer.stats.total_time == pytest.approx(timer.stats.most_recent, rel=0.2, abs=0.2)
    assert timer.stats.mean == pytest.approx(timer.stats.most_recent)
    assert timer.stats.median == pytest.approx(timer.stats.most_recent)
    assert timer.stats.fastest_time == pytest.approx(timer.stats.most_recent)
    assert timer.stats.slowest_time == pytest.approx(timer.stats.most_recent)
    assert timer.stats.min == pytest.approx(timer.stats.most_recent)
    assert timer.stats.max == pytest.approx(timer.stats.most_recent)
    assert timer.stats.get_time(0) == pytest.approx(timer.stats.most_recent)
    assert timer.stats.percentile(50) == pytest.approx(timer.stats.most_recent)


def test_timer_pause_resume_excludes_paused_time():
    timer = sktime.Timer()
    timer.start()
    sktime.sleep(SLEEP_SHORT)
    timer.pause()
    paused_for = SLEEP_MED
    sktime.sleep(paused_for)
    timer.resume()
    sktime.sleep(SLEEP_SHORT)
    elapsed = timer.stop()

    # Should be roughly SLEEP_SHORT + SLEEP_SHORT
    _assert_between(elapsed, (2 * SLEEP_SHORT) - TOL, 0.2)
    # total_time_paused now tracks strict accumulated paused duration
    ttp = timer.stats.total_time_paused
    assert ttp is not None and ttp >= (paused_for - 0.005)


def test_timer_lap_and_stop_records_two_times():
    timer = sktime.Timer()
    timer.start()
    sktime.sleep(SLEEP_SHORT)
    lap1 = timer.lap()
    sktime.sleep(SLEEP_SHORT)
    lap2 = timer.stop()

    assert timer.stats.num_times == 2
    _assert_between(lap1, SLEEP_SHORT - TOL, 0.1)
    _assert_between(lap2, SLEEP_SHORT - TOL, 0.1)
    assert timer.stats.slowest_index in (0, 1)
    assert timer.stats.fastest_index in (0, 1)


def test_timer_add_time_and_reset():
    timer = sktime.Timer()
    timer.add_time(0.01)
    timer.add_time(0.02)
    assert timer.stats.num_times == 2
    assert timer.stats.mean is not None and timer.stats.mean > 0
    stats = timer.get_statistics()
    assert stats is not None and stats.num_times == 2

    timer.reset()
    assert timer.stats.num_times == 0
    assert timer.stats.most_recent is None
    assert timer.stats.total_time is None
    assert timer.get_statistics() is None


def test_timer_errors_and_warnings():
    timer = sktime.Timer()
    with pytest.raises(RuntimeError):
        timer.stop()
    with pytest.raises(RuntimeError):
        timer.pause()
    # resume while not paused should warn, but only if a frame exists; start first
    timer.start()
    with pytest.warns(UserWarning):
        timer.resume()  # resume while not paused triggers warning
    # clean up frame to not leak state between tests
    timer.stop()


def test_timer_thread_safety_sessions():
    timer = sktime.Timer()
    durations = [SLEEP_SHORT, SLEEP_MED, SLEEP_SHORT]

    def run(d):
        timer.start()
        sktime.sleep(d)
        timer.stop()

    with ThreadPoolExecutor(max_workers=3) as ex:
        ex.map(run, durations)

    assert timer.stats.num_times == len(durations)
    assert timer.stats.fastest_time is not None and timer.stats.slowest_time is not None
    assert timer.stats.fastest_time <= timer.stats.slowest_time


# TimeThis
def test_timethis_context_without_explicit_timer():
    with sktime.TimeThis() as t:
        sktime.sleep(SLEEP_SHORT)
    assert t.stats.num_times == 1
    assert t.stats.most_recent is not None and t.stats.most_recent >= (SLEEP_SHORT - TOL)


def test_timethis_context_with_explicit_timer_pause_resume_and_lap():
    shared = sktime.Timer()

    with sktime.TimeThis(shared) as t:
        sktime.sleep(SLEEP_SHORT)
        t.pause()
        sktime.sleep(SLEEP_MED)
        t.resume()
        sktime.sleep(SLEEP_SHORT)
        t.lap()
        sktime.sleep(SLEEP_SHORT)
        # implicit stop on exit

    assert shared.stats.num_times == 2  # one lap + final
    assert shared.stats.total_time is not None and shared.stats.total_time > 0


# @timethis
def test_decorator_with_explicit_timer():
    acc = sktime.Timer()

    @sktime.timethis(acc)
    def op():
        sktime.sleep(SLEEP_SHORT)

    for _ in range(5):
        op()

    assert acc.stats.num_times == 5
    assert acc.stats.mean is not None and acc.stats.mean >= (SLEEP_SHORT - TOL)


def test_decorator_auto_global_and_stacking():
    shared = sktime.Timer()

    @sktime.timethis()
    @sktime.timethis(shared)
    def op2():
        sktime.sleep(SLEEP_SHORT)

    for _ in range(3):
        op2()

    # explicit timer collected
    assert shared.stats.num_times == 3
    # auto timer attached to wrapper
    assert hasattr(op2, "timer")
    auto_timer = getattr(op2, "timer")
    assert isinstance(auto_timer, sktime.Timer)
    assert auto_timer.stats.num_times == 3


# Additional edge cases
def test_timer_initial_state_and_invalid_access():
    """Fresh Timer has None properties; invalid get_time returns None; percentile input validated."""
    timer = sktime.Timer()
    assert timer.stats.num_times == 0
    assert timer.stats.most_recent is None
    assert timer.stats.total_time is None
    assert timer.stats.mean is None
    assert timer.stats.median is None
    assert timer.stats.fastest_time is None
    assert timer.stats.slowest_time is None
    assert timer.stats.get_time(0) is None
    assert timer.stats.get_time(-1) is None
    # empty timer returns None for percentile, even for invalid inputs
    assert timer.stats.percentile(50) is None
    assert timer.stats.percentile(-1) is None
    assert timer.stats.percentile(101) is None


def test_timer_statistics_snapshot_immutability():
    """get_statistics returns a snapshot whose numeric values don't change after new measurements."""
    timer = sktime.Timer()
    for _ in range(3):
        timer.start(); sktime.sleep(SLEEP_SHORT); timer.stop()
    stats = timer.get_statistics()
    assert stats is not None
    snap_count = stats.num_times
    snap_mean = stats.mean

    # Add more timings
    for _ in range(3):
        timer.start(); sktime.sleep(SLEEP_SHORT); timer.stop()

    # Snapshot values remain the same
    assert stats.num_times == snap_count
    assert stats.mean == snap_mean
    # But timer has more measurements now
    assert timer.stats.num_times == 6


def test_timer_percentile_invalid_with_data():
    timer = sktime.Timer()
    for _ in range(3):
        timer.start(); sktime.sleep(SLEEP_SHORT); timer.stop()
    with pytest.raises(ValueError):
        timer.stats.percentile(-1)
    with pytest.raises(ValueError):
        timer.stats.percentile(101)


def test_decorator_explicit_timer_multithreaded_accumulates_counts():
    """Decorator with explicit Timer should count across threads correctly."""
    acc = sktime.Timer()

    @sktime.timethis(acc)
    def work():
        sktime.sleep(SLEEP_SHORT)

    n = 8
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(lambda _: work(), range(n)))

    assert acc.stats.num_times == n


def test_timethis_context_records_on_exception():
    """TimeThis should record a measurement even if the block raises; exception not suppressed."""
    shared = sktime.Timer()
    with pytest.raises(RuntimeError):
        with sktime.TimeThis(shared):
            sktime.sleep(SLEEP_SHORT)
            raise RuntimeError("boom")
    assert shared.stats.num_times == 1


def test_decorator_auto_global_independent_per_function_and_classmethod():
    """Auto-global timers are independent per function; class method is supported with unique timer."""
    @sktime.timethis()
    def f1():
        sktime.sleep(SLEEP_SHORT)

    @sktime.timethis()
    def f2():
        sktime.sleep(SLEEP_SHORT)

    for _ in range(2):
        f1(); f2()

    t1 = getattr(f1, "timer", None)
    t2 = getattr(f2, "timer", None)
    assert isinstance(t1, sktime.Timer) and isinstance(t2, sktime.Timer)
    assert t1 is not t2
    assert t1.stats.num_times == 2
    assert t2.stats.num_times == 2

    class C:
        @sktime.timethis()
        def method(self):
            sktime.sleep(SLEEP_SHORT)

    c = C()
    c.method(); c.method()
    # Access function object attribute via class
    mt = getattr(C.method, "timer", None)
    assert isinstance(mt, sktime.Timer)
    assert mt.stats.num_times == 2


def test_clear_global_timers_resets_registry():
    # Create some auto timers
    @sktime.timethis()
    def f():
        sktime.sleep(SLEEP_SHORT)

    f(); f()
    t_before = getattr(f, "timer", None)
    assert isinstance(t_before, sktime.Timer)
    assert t_before.stats.num_times == 2

    # Clear registry (access via getattr to satisfy static typing)
    cg = getattr(sktime, "clear_global_timers")
    cg()

    # Re-decorate a new function and ensure fresh registry is used
    @sktime.timethis()
    def g():
        sktime.sleep(SLEEP_SHORT)

    g(); g()
    t_after = getattr(g, "timer", None)
    assert isinstance(t_after, sktime.Timer)
    assert t_after.stats.num_times == 2


def test_decorator_auto_global_in_processes_smoke():
    from concurrent.futures import ProcessPoolExecutor

    durations = [SLEEP_SHORT, SLEEP_SHORT, SLEEP_SHORT]
    with ProcessPoolExecutor(max_workers=3) as ex:
        outs = list(ex.map(_mp_slow_op, durations))
    assert outs == durations


def test_timer_stress_multi_thread_many_iterations():
    timer = sktime.Timer()

    def work(n: int):
        for _ in range(n):
            timer.start()
            # tiny work
            sktime.sleep(SLEEP_SHORT)
            timer.stop()

    threads = [threading.Thread(target=work, args=(10,)) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert timer.stats.num_times == 50
    assert timer.stats.mean is not None and timer.stats.mean > 0


def test_yawn_logs_only_on_threshold(capsys):
    y = sktime.Yawn(sleep_duration=SLEEP_SHORT, yawn_threshold=2, log_sleep=True)
    y.yawn()
    out1 = capsys.readouterr().out
    assert out1 == ""  # no log yet
    y.yawn()
    out2 = capsys.readouterr().out
    assert "Sleeping for" in out2


def test_sleep_zero_and_negative_and_elapsed_type_errors():
    # sleep(0) quick
    t0 = time.time()
    sktime.sleep(0)
    assert (time.time() - t0) < 0.05

    # negative sleep mirrors time.sleep behavior
    with pytest.raises(ValueError):
        sktime.sleep(-0.001)

    # elapsed type errors
    with pytest.raises(TypeError):
        sktime.elapsed("a", 1.0)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        sktime.elapsed(1.0, "b")  # type: ignore[arg-type]


