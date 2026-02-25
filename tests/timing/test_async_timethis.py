from suitkaise import timing
import asyncio

@timing.timethis()
async def my_function():
    await asyncio.sleep(1)

asyncio.run(my_function())
print(my_function.timer.mean)