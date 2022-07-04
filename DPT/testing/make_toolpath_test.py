import time

from DPT.DATA.op_data.op_data import OpData
from DPT.INTERFACE.eva import EvaInterface
from DPT.CONTROL.broker import Broker

from multiprocessing import Process

def Eva():
    eva = EvaInterface()
    eva.make_toolpath([0,1,2,1])

def Data():
    data = OpData()
    data.listen()

def DPTBroker():
    broker = Broker()
    broker.mediate()


if __name__ == "__main__":
    p_eva = Process(target=Eva)
    p_data = Process(target=Data)
    p_broker = Process(target=DPTBroker)
    p_broker.start()
    p_data.start()
    p_eva.start()

    p_eva.join()
    print("Eva finished")
    p_data.terminate()
    p_broker.terminate()
