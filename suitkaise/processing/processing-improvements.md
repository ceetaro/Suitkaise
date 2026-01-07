# processing and cerial improvements

---

## processing: Pool

and also, on another road, we can do this:

add a pooling option

from suitkaise import processing

pool = processing.Pool(max_workers=8)

the main difference is that Pool serializes with cerial and accepts objects of type ["processing.Process"]

pool.map(my_function, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

pool.map(class of type["processing.Process"], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

---

## processing.Process: tell and listen

we need methods to communicate while processes are running.

i think 2 methods, `tell` and `listen`.

tell sends data to the other side.

so if the parent calls tell, that data is sent to the subprocess. if the subprocess calls listen, it will receive the data from the parent's tell.

and vice versa. if the parent calls listen, it will wait until the subprocess calls tells and sends data.

listen is blocking, tell is not.


---


change result property to result()
