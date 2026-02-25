from suitkaise.processing import Pool, Share, Skprocess
from suitkaise.timing import Sktimer, TimeThis
from suitkaise.circuits import BreakingCircuit
from suitkaise.paths import Skpath
import logging


# define a process class that inherits from Skprocess
class MyProcess(Skprocess):
    def __init__(self, item, share: Share):
        self.item = item
        self.share = share

        self.local_results = []

        # set the number of runs (times it loops)
        self.process_config.runs = 3

    # setup before main work
    def __prerun__(self):
        if self.share.circuit.broken:
            # subprocesses can stop themselves
            self.stop()
            return

    # main work
    def __run__(self):

        self.item = self.item * 2
        self.local_results.append(self.item)

        self.share.results.append(self.item)
        self.share.results.sort()

    # cleanup after main work
    def __postrun__(self):
        self.share.counter += 1
        self.share.log.info(f"Processed {self.item / 2} -> {self.item}, counter: {self.share.counter}")

        if self.share.counter > 50:
            print("Numbers have been doubled 50 times, stopping...")
            self.share.circuit.short()

        self.share.timer.add_time(self.__run__.timer.most_recent)


    def __result__(self):
        return self.local_results


def main():

    # Share is shared state across processes
    # all you have to do is add things to Share, otherwise its normal Python
    share = Share()
    share.counter = 0
    share.results = []
    share.circuit = BreakingCircuit(
        num_shorts_to_trip=1,
        sleep_time_after_trip=0.0,
    )
    # Skpath() gets your caller path
    logger = logging.getLogger(str(Skpath()))
    logger.handlers.clear()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    logger.propagate = False
    share.log = logger
    share.timer = Sktimer()

    with TimeThis() as t:
        with Pool(workers=4) as pool:
            # star() modifier unpacks tuples as function arguments
            results = pool.star().map(MyProcess, [(item, share) for item in range(100)])

    print(f"Counter: {share.counter}")
    print(f"Results: {share.results}")
    print(f"Time per run: {share.timer.mean}")
    print(f"Total time: {t.most_recent}")
    print(f"Circuit total trips: {share.circuit.total_trips}")
    print(f"Results: {results}")


if __name__ == "__main__":
    main()