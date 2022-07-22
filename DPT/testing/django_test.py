import time

import zmq

from DPT.DATA.op_data.op_data import OpData
from DPT.INTERFACE.eva import EvaInterface
from DPT.CONTROL.broker import Broker


from multiprocessing import Process, Event


def Eva(stop: Event):
    with EvaInterface() as eva:
        stop.wait()

def Data():
    data = OpData()

def DPTBroker():
    broker = Broker()
    broker.mediate()

if __name__ == "__main__":
    stop_eva = Event()

    p_eva = Process(target=Eva, args=(stop_eva,))
    p_data = Process(target=Data)
    p_broker = Process(target=DPTBroker)

    p_broker.start()
    p_data.start()
    p_eva.start()

    time.sleep(3)
    input("Press Enter to stop")
    stop_eva.set()

    p_eva.join()
    p_data.terminate()
    p_broker.terminate()
