import time

from DPT.DATA.op_data.op_data import OpData
from DPT.INTERFACE.eva.eva import EvaInterface

import asyncio


async def main():
    op_data = OpData()
    eva_interface = EvaInterface()
    await asyncio.gather(op_data.awaitable, eva_interface.awaitable)


if __name__ == "__main__":

    asyncio.run(main())

    input("Press Enter to stop")
