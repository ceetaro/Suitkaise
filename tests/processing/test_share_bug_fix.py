from suitkaise.processing import Pool, Share
from suitkaise.timing import Sktimer, TimeThis
from suitkaise.circuits import BreakingCircuit
from suitkaise.paths import Skpath
import logging


def process(item, share: Share):
    if share.circuit.broken:
        return

    with TimeThis() as timer:
        result = item * 2
        share.results.append(result)
        share.results = sorted(share.results)
        share.counter += 1
        share.log.info(f"Processed {item} -> {result}, counter: {share.counter}")

        if share.counter > 50:
            share.circuit.short()


    share.timer.add_time(timer.most_recent)


def main():
    share = Share()
    share.counter = 0
    share.results = []
    share.circuit = BreakingCircuit(
        num_shorts_to_trip=1,
        sleep_time_after_trip=0.0,
    )
    share.log = logging.getLogger(str(Skpath()))
    share.log.addHandler(logging.StreamHandler())
    share.log.setLevel(logging.INFO)
    share.timer = Sktimer()

    with Pool(workers=4) as pool:
        pool.star().map(process, [(item, share) for item in range(100)])

    print(share.counter)
    print(share.results)
    print(share.timer.mean)
    print(share.circuit.total_trips)


if __name__ == "__main__":
    main()