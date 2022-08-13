import zmq
import time
import asyncio
from dpt_module import DptModule


mod = DptModule()
time.sleep(1)

async def sayhi():
    await mod.client_transmit("comm_testing-router-1", "hi")
    msg = await mod.client_receive("comm_testing-router-1", 100)
    print(msg)

async def main():
    success = await mod.register_connection("comm_testing-router-1")
    a = asyncio.create_task(mod.client_loop())
    if success:
        print("connection successful")
        b = asyncio.create_task(sayhi())
    else:
        print("could not connect")

    await a
    await b

asyncio.run(main())