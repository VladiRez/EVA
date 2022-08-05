import zmq
import time
import asyncio
from dpt_module import DptModule



mod = DptModule()
async def monitor():
    while True:
        (sender, msg) = await mod.server_msg_queue.get()
        if msg == "hi":
            await mod.server_transmit(sender, "hi zurueck")
            break

async def main():
    a = asyncio.create_task(mod.monitor_server_socket())
    b = asyncio.create_task(monitor())
    await a
    await b

asyncio.run(main())
time.sleep(30)
