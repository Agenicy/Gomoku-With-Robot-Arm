import serial  # 引用pySerial模組
import binascii
import threading
from time import sleep, time

class client(threading.Thread):
    def __init__(self, signal, port='COM4', baud=9600, show = False):
        threading.Thread.__init__(self)
        self.singal = signal # thread flag
        self.show = show
        self.COM_PORT = port
        self.BAUD_RATES = baud
        self.ser = serial.Serial(self.COM_PORT, self.BAUD_RATES)   # 初始化序列通訊埠
        
        self.dataBuffer = []
        self.state = 1
    
    # ---------------------------------------------------------------------

    def run(self):
        """ communicate with client
        
            prorocol
        
                0- X 
                1- [server] allow sending / [client] online 
                2- [server] stay there! / [client] is waiting

                3 + num - [server] throw data, size of data / [client] got 3, start receive data
                4- [server] done. / [client] ACK
                5- [Client] NAK (timeout) -> throw again
                6- [server] reset client"""
                
        while True:
            sleep(0.3)
            if self.state == 1:
                self.WaitForJoin()
                
            elif self.state == 2:
                self.ClientStay()
                """self.Send([1,2,3,4,5,6]) # test
                self.state = 3"""
                self.WaitingForUserSend()
                
            elif self.state == 3:
                self.PrepareSend()
                
            elif self.state == 4:
                self.SendBatch()
            
    def WaitForJoin(self): # wating for 1
        """ [Blocking] wait until get 1, if got the other data will reset client"""
        d = self.GetData(cmd=1, time=2)
        if self.show:
            print(f'state = {self.state}')
        if d == 1:
            # Client online
            print(f'Here comes a new client.')
            self.state = 2
        else:
            self.ResetClient()
    
    def ClientStay(self): # waiting for 2
        """ [Blocking] wait until get 2"""
        d = self.GetData(2)
        if d == 2:
            # Client online
            if self.show:
                print(f'Serial Passage Created.')
            self.state = 2
        else:
            self.ResetClient()
            sleep(0.3)
           
    def WaitingForUserSend(self):
        self.singal.wait()
        self.singal.clear()
        self.state = 3
            
    def PrepareSend(self):
        if len(self.dataBuffer) > 0:
            while self.state == 3:
                self.Send(3)
                self.Send(len(self.dataBuffer))
                if self.GetData() == 3:
                    self.state = 4
                    print('start sending')
                else:
                    print('nak')
        else:
            self.state = 2
                    
         
    def SendBatch(self):
        """ client in state 4, start sending data"""
        def printDataBuffer():
            sb = "send: "
            for i in self.dataBuffer:
                 sb += str(i) + ','
            print(sb[:-1])
        
        data_length = 7
        for d in range(0, data_length):
            self.Send(self.dataBuffer[d])
        printDataBuffer()
        client_state = self.GetData(4)
        if client_state == 4:
            # ACK
            self.dataBuffer = self.dataBuffer[data_length:]
            if len(self.dataBuffer) == 0:
                self.state = 2
            else:
                self.state = 3
            if self.show:
                print('ACK')
        elif client_state == 5:
            self.state = 3
            print('NAK')
        else:
            print(f'[Warning]: {client_state}')
    
    # ---------------------------------------------------------------------
    def GetData(self, cmd=None, time = 0.1):
        """[Blocking] read a byte"""
        while not self.ser.in_waiting:
            if type(cmd) is int:
                self.Send(cmd)
                sleep(time)
            elif type(cmd) is list:
                self.Send(cmd[0])
                self.Send(cmd[1])
                sleep(time)
        ret = self.ser.readline().decode().replace('\n','')  # 讀取一行
        if self.show:
            print(f'state {self.state}, get {ret}')
        return int(ret)

    def Send(self, data):
        """ Send a byte, or lists of byte"""
        if type(data) is int:
            # send a byte
            """if self.show:
                print(f'send {data.to_bytes(1, byteorder="big")}')"""
            self.ser.write(data.to_bytes(1, byteorder='big'))
        elif type(data) is list:
            for d in data:
                if self.show:
                    print(f'data add {d}')
                self.dataBuffer.append(d)
        else:
            raise Exception('Wrong datatype.')

    def SerialSend(self, data):
        """ [Public] send data, used by usb()"""
        for d in data:
            self.dataBuffer.append[d]

    def ResetClient(self):
        self.dataBuffer = []
        self.state = 1
        sleep(1)
    

class usb():
    def __init__(self):
        """ create a class to handle serial port"""
        super().__init__()
        print('usb start...')
        self.client = {} #clients, now must be only 1 client
        self.thread = [] #list of threads
        self.singal = threading.Event()

    def AddClient(self, port, baud, show = False, testMode = False):
        if not testMode:
            if len(self.client) == 0:
                self.client[port] = client(signal = self.singal,port=port, baud=baud, show= show) # add client
        else:
            self.client[port] = Dummy(signal = self.singal,port=port, baud=baud, show= show) # add client
        print('Client added...')

    def Run(self):
        if len(self.client) == 0:
            raise Exception('NO Client!')
        try:
            print('Client running...')
            for c in self.client.values(): # run clients
                if not c.isAlive():
                    c.start()
        except KeyboardInterrupt:
            self.Close()
            print('bye.')

    def Send(self, data, port = 'COM4'):
        try:
            self.client[port].Send(data)
            self.singal.set()
        except Exception as e:
            print(e)

    def UserSend(self, data=None, port='COM4'):
        print(f'[UserSend] {data}')
        self.Wait(port=port)
        try:
            word = []
            if data is None:
                word = input(f'Enter Data, use dot(".") to seprate...').replace('\n','').split('.')
            else:
                word = data
                
            for i in range(len(word)):
                word[i] = int(word[i])
                
            # print('Get Your Command. Start Sending...')
            self.Send(word, port)
        except Exception as e:
            print(e)

    def Wait(self, port = 'COM4'):
        sleep(0.5)
        while not self.client[port].state == 2:
            print(f"[ERROR] can't send because {port}.state is {self.client[port].state}")
            sleep(0.2)
        sleep(0.5)
        return None

    def Close(self):
        """ close all client and threads"""
        for c in self.client.values():
            c.ser.close()
        for t in self.thread:
            t.join()


from random import randint
class Dummy(threading.Thread):
    def __init__(self, signal, port='COM4', baud=9600, show = False):
        threading.Thread.__init__(self)
        self.singal = signal # thread flag
        self.show = show
        self.COM_PORT = port
        self.BAUD_RATES = baud
        
        self.dataBuffer = []
        self.state = 1
    
    # ---------------------------------------------------------------------

    def run(self):
        while True:
            sleep(0)
            if self.state == 1:
                self.WaitForJoin()
                
            elif self.state == 2:
                self.ClientStay()
                self.WaitingForUserSend()
                
            elif self.state == 3:
                self.PrepareSend()
                
            elif self.state == 4:
                self.SendBatch()
            
    def WaitForJoin(self): # wating for 1
        """ [Blocking] wait until get 1, if got the other data will reset client"""
        d = self.GetData(cmd=1, time=2)
        if self.show:
            print(f'state = {self.state}')
        if d == 1:
            # Client online
            if self.show:
                print(f'Here comes a new client.')
            self.state = 2
        else:
            self.ResetClient()
    
    def ClientStay(self): # waiting for 2
        """ [Blocking] wait until get 2"""
        d = self.GetData(2)
        if d == 2:
            # Client online
            if self.show:
                print(f'Serial Passage Created.')
            self.state = 2
        else:
            self.ResetClient()
            sleep(0)
           
    def WaitingForUserSend(self):
        self.singal.wait()
        self.singal.clear()
        self.state = 3
            
    def PrepareSend(self):
        if len(self.dataBuffer) > 0:
            while self.state == 3:
                self.Send(3)
                self.Send(len(self.dataBuffer))
                if self.GetData() == 3:
                    self.state = 4
                    if self.show:
                        print('start sending')
                else:
                    if self.show:
                        print('nak')
         
    def SendBatch(self):
        """ client in state 4, start sending data"""
        def printDataBuffer():
            sb = "send: "
            for i in self.dataBuffer:
                 sb += str(i) + ','
            print(sb[:-1])
            
        data_length = 7
        for d in range(data_length):
            self.Send(self.dataBuffer[d])
        printDataBuffer()
        client_state = self.GetData(4)
        if client_state == 4:
            # ACK
            self.dataBuffer = self.dataBuffer[data_length:]
            if len(self.dataBuffer) == 0:
                self.state = 2
            else:
                print(f'[FATAL WARRING] self.dataBuffer = {self.dataBuffer}')
                while True:
                    sleep(999)
            if self.show:
                print('ACK')
        elif client_state == 5:
            self.state = 3
            print('NAK')
        else:
            print(f'[Warning]: {client_state}')
    
    # ---------------------------------------------------------------------
    def GetData(self, cmd=None, time = 0.3):
        sleep(0)
        return cmd if not cmd is None else 3

    def Send(self, data):
        """ Send a byte, or lists of byte"""
        if type(data) is int:
            # send a byte
            if self.show:
                print(f'send {data.to_bytes(1, byteorder="big")}')
        elif type(data) is list:
            for d in data:
                if self.show:
                    print(f'data add {d}')
                self.dataBuffer.append(d)
        else:
            raise Exception('Wrong datatype.')

    def SerialSend(self, data):
        """ [Public] send data, used by usb()"""
        for d in data:
            self.dataBuffer.append[d]

    def ResetClient(self):
        self.dataBuffer = []
        self.state = 1
        sleep(1)


if __name__ == "__main__":
    usb = usb()
    usb.AddClient('COM4', 9600, show = True)
    usb.Run()
    while True:
        sleep(1)
        usb.UserSend()
    usb.Close()
