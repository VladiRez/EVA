import time

from DPT.DATA.op_data.op_data import OpData
from DPT.INTERFACE.eva import EvaInterface
from DPT.CONTROL.broker import Broker
from DPT.UI.process_ui import manage

from multiprocessing import Process

def Eva():
    eva = EvaInterface()

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
    #p_ui = Process(target=UI)
    p_broker.start()
    p_data.start()
    p_eva.start()

    time.sleep(30)
    p_eva.join()
    print("Eva finished")
    p_data.terminate()
    p_broker.terminate()
