# some simple python code
counter = 0
results = []
log = logging.getLogger("worker")

def process(item):
    result = item * 2
    results.append(result)
    counter += 1
    log.info(f"done: {result}")



then, we expand the code.

from suitkaise import Share

# still just as simple
share = Share()

share.counter = 0
share.results = []
share.log = logging.getLogger("worker")

def process(item):
    result = item * 2
    share.results.append(result)
    share.counter += 1
    share.log.info(f"done: {result}")



then, when comparing to mp.Manager


share = Share()

share.counter = 0
share.results = []
share.log = logging.getLogger("worker")

def process(item):
    result = item * 2
    share.results.append(result)
    share.counter += 1
    share.log.info(f"done: {result}")


pool = Pool(workers=4)
pool.star().map(process, [(x, share) for x in range(4)])




from multiprocessing import Process, Manager

manager = Manager()
counter = manager.Value('i', 0)
lock = manager.Lock()
results = manager.list()
# NO LOGGER ✗

def process(item):
    result = item * 2
    results.append(result)
    with lock:
        counter.value += 1
    # NO LOGGER ✗

workers = []
for i in range(4):
    p = Process(target=process, args=(i,))
    p.start()
    workers.append(p)
for p in workers:
    p.join()