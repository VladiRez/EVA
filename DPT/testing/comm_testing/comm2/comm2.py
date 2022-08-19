import zmq
import time
import asyncio
import logging
from dpt_module import DptModule



mod = DptModule()

async def monitor():
    while True:
        (sender, msg) = await mod.server_receive()
        if msg == "hi":
            logging.info(msg)
            await mod.server_transmit(sender, "hi zurueck")
            break

async def main():
    a = asyncio.create_task(mod.server_loop())
    b = asyncio.create_task(monitor())
    await asyncio.sleep(10)
    logging.info("Going offline")
    a.cancel()
    await asyncio.sleep(15)
    logging.info("going online")
    a = asyncio.create_task(mod.server_loop())
    await asyncio.sleep(10)
    a.cancel()
    try:
        await a
    except asyncio.CancelledError:
        pass
        await b

asyncio.run(main())
