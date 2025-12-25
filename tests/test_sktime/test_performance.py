import time
from time import perf_counter

import pytest  # type: ignore

from suitkaise import sktime


# Simple micro-benchmark harness
def _measure_avg_seconds(fn, iterations: int = 2000, warmup: int = 100) -> float:
    for _ in range(warmup):
        fn()
    t0 = perf_counter()
    for _ in range(iterations):
        fn()
    t1 = perf_counter()
    return (t1 - t0) / iterations


def _color(s: str, color_code: str) -> str:
    return f"\033[{color_code}m{s}\033[0m"


def _print_result(name: str, value: float, unit: str = "s") -> None:
    print(_color(f"{name:40} ", "36") + _color(f"{value:.6f} {unit}", "32"))


@pytest.mark.benchmark
def test_perf_time_vs_time_time():
    avg_time_time = _measure_avg_seconds(lambda: time.time())
    avg_sktime_time = _measure_avg_seconds(lambda: sktime.time())

    _print_result("time.time() avg call", avg_time_time)
    _print_result("sktime.time() avg call", avg_sktime_time)

    # Overhead should be near-equal; allow generous factor for CI noise
    assert avg_sktime_time / (avg_time_time or 1e-12) < 3.0


@pytest.mark.benchmark
def test_perf_elapsed_vs_manual():
    # manual two-arg elapsed using time.time() and abs subtraction
    def manual_two_arg():
        t1 = time.time(); t2 = time.time(); _ = abs(t2 - t1)

    def sk_elapsed_two_arg():
        t1 = sktime.time(); t2 = sktime.time(); _ = sktime.elapsed(t1, t2)

    avg_manual = _measure_avg_seconds(manual_two_arg)
    avg_sktime = _measure_avg_seconds(sk_elapsed_two_arg)

    _print_result("manual elapsed (two-arg) avg", avg_manual)
    _print_result("sktime.elapsed(two-arg) avg", avg_sktime)

    # Should be within a small constant factor
    assert avg_sktime / (avg_manual or 1e-12) < 2.5


@pytest.mark.benchmark
def test_perf_timer_start_stop_noop():
    timer = sktime.Timer()
    avg = _measure_avg_seconds(lambda: (timer.start(), timer.stop()))
    _print_result("Timer start+stop (noop) avg", avg)
    # Upper bound per-iteration (very generous)
    assert avg < 0.002


@pytest.mark.benchmark
def test_perf_timer_lap_noop():
    timer = sktime.Timer()
    def lap_once():
        timer.start(); timer.lap(); timer.stop()
    avg = _measure_avg_seconds(lap_once)
    _print_result("Timer start+lap+stop (noop) avg", avg)
    assert avg < 0.003


@pytest.mark.benchmark
def test_perf_timer_pause_resume_noop():
    timer = sktime.Timer()
    def pause_resume_once():
        timer.start(); timer.pause(); timer.resume(); timer.stop()
    avg = _measure_avg_seconds(pause_resume_once)
    _print_result("Timer start+pause+resume+stop avg", avg)
    assert avg < 0.004


@pytest.mark.benchmark
def test_perf_timethis_context_overhead():
    def with_context():
        with sktime.TimeThis():
            pass
    avg_cm = _measure_avg_seconds(with_context)
    _print_result("TimeThis context (empty) avg", avg_cm)
    assert avg_cm < 0.003


@pytest.mark.benchmark
def test_perf_decorator_overhead_vs_plain():
    def plain():
        return 1

    avg_plain = _measure_avg_seconds(plain)

    @sktime.timethis()
    def wrapped():
        return 1

    avg_wrapped = _measure_avg_seconds(wrapped)
    _print_result("plain call avg", avg_plain)
    _print_result("@timethis wrapped call avg", avg_wrapped)

    # Wrapped call absolute overhead should remain very small
    ratio = avg_wrapped / (avg_plain or 1e-12)
    assert avg_wrapped < 1e-5
    assert ratio < 200.0


@pytest.mark.benchmark
def test_perf_yawn_no_sleep_overhead():
    # Ensure no sleeps: large threshold, zero sleep_duration
    y = sktime.Yawn(sleep_duration=0.0, yawn_threshold=10_000)
    avg = _measure_avg_seconds(lambda: y.yawn())
    _print_result("Yawn (no sleep) call avg", avg)
    assert avg < 0.001


if __name__ == "__main__":
    print(_color("SKTime Benchmarks", "35"))
    start = perf_counter()
    test_perf_time_vs_time_time()  # type: ignore
    test_perf_elapsed_vs_manual()  # type: ignore
    test_perf_timer_start_stop_noop()  # type: ignore
    test_perf_timer_lap_noop()  # type: ignore
    test_perf_timer_pause_resume_noop()  # type: ignore
    test_perf_timethis_context_overhead()  # type: ignore
    test_perf_decorator_overhead_vs_plain()  # type: ignore
    test_perf_yawn_no_sleep_overhead()  # type: ignore
    print(_color(f"Completed in {perf_counter()-start:.3f}s", "33"))

