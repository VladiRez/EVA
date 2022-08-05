import zmq
import time
import asyncio
from dpt_module import DptModule


mod = DptModule()
time.sleep(1)

async def main():
    success = await mod.register_connection("comm_testing-router-1")
    if success:
        print("connection successful")
        await mod.client_transmit("comm_testing-router-1", "hi")
        msg = await mod.client_receive("comm_testing-router-1")
    else:
        print("could not connect")

asyncio.run(main())