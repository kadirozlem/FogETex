import logging
import sys
from threading import Thread, Timer, Event
from enum import Enum
import time
import datetime
import socketio
from Application import GaitAnalysis
import json
import os
import Config

GaitAnalysis.ReadAllData()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def now():
    return datetime.datetime.now().timestamp()


class WorkerType(Enum):
    SERVER = 1
    MASTER = 2
    WORKER = 3


class SetInterval():
    def __init__(self, increment, tick_event):
        self.tick_event = tick_event
        self.next_t = time.time()
        self.i = 0
        self.done = False
        self.increment = increment
        self._run()

    def _run(self):
        self.tick_event()
        self.next_t += self.increment
        self.i += 1
        if not self.done:
            Timer(self.next_t - time.time(), self._run).start()

    def stop(self):
        self.done = True


class ResultWriter:
    ThreadTimeInfo = {}
    ThreadInformations = {}
    ResourceInfo = {}

    def __init__(self):
        self.directory = Config.Configuration.FileDirectory + datetime.datetime.today().strftime(
            '%Y_%m_%d___%H_%M_%S') + Config.Configuration.FilePostfix + "/"
        os.mkdir(self.directory)
        self.timer = SetInterval(Config.Configuration.FileWritePeriod, self.TimerEvent)

    def TimerEvent(self):
        self.WriteData()
        self.WriteResourceInfo()
        self.WriteThreadInformations()

    def WriteData(self):
        temp_dict = ResultWriter.ThreadTimeInfo
        ResultWriter.ThreadTimeInfo = {}
        for i in temp_dict:
            filename = self.directory + str(i) + ".csv"
            answ = os.path.exists(filename)
            with open(filename, "a" if answ else "w") as f:
                f.writelines(temp_dict[i])

    def WriteResourceInfo(self):
        temp_dict = ResultWriter.ResourceInfo
        ResultWriter.ResourceInfo = {}
        for i in temp_dict:
            filename = self.directory + "resource__" + i.replace(':', '_').replace('/', '_').replace('.', '_') + ".json"
            answ = os.path.exists(filename)
            with open(filename, "a" if answ else "w") as f:
                f.writelines(temp_dict[i])

    def WriteThreadInformations(self):
        temp_dict = ResultWriter.ThreadInformations
        ResultWriter.ThreadInformations = {}
        for i in temp_dict:
            filename = self.directory + str(i) + "_ThreadInformation.csv"
            answ = os.path.exists(filename)
            with open(filename, "a" if answ else "w") as f:
                f.writelines(temp_dict[i])

    @staticmethod
    def AddThreadTimeInformation(thread_no, record):
        timeInfo = ResultWriter.ThreadInformations.get(thread_no)
        if threadInfo is None:
            ResultWriter.ThreadTimeInfo[thread_no] = [record + "\n"]
        else:
            timeInfo.append(record + "\n")

    @staticmethod
    def AddResourceInformation(url, info):
        resourceInfo = ResultWriter.ResourceInfo.get(url)
        if resourceInfo is None:
            ResultWriter.ResourceInfo[url] = [json.dumps(info) + "\n"]
        else:
            resourceInfo[url].append(json.dumps(info) + "\n")

    @staticmethod
    def AddTheadInformation(thread_no, record):
        threadInfo = ResultWriter.ThreadInformations.get(thread_no)
        if threadInfo is None:
            ResultWriter.ThreadInformations[thread_no] = [record + "\n"]
        else:
            threadInfo.append(record + "\n")


class FogTester(Thread):
    ThreadCount = 0
    ClosedThreads = 0
    threads = []
    resource_threads = {}

    def __init__(self, i, url, worker_port, resource_port, application, test_type):
        Thread.__init__(self)
        self.i = i
        self.url = url
        self.WorkerPort = worker_port
        self.ResourcePort = resource_port
        self.SamplingPeriod = Config.Configuration.SamplingPeriod
        self.FogProcessIsReady = False
        self.FogConnected = False
        self.Application = application
        self.TestType = test_type
        self.data_index = 0
        self.err = False
        ResultWriter.AddTheadInformation(i, "Feature;Value")
        ResultWriter.AddTheadInformation(i, "DeviceURL;" + self.Application.Name)
        ResultWriter.AddTheadInformation(i, "TestType;" + Config.TestType.getName(self.TestType))
        ResultWriter.AddTheadInformation(i, "DeviceURL;" + self.url)
        ResultWriter.AddTheadInformation(i, "ThreadCreated;" + str(now()))
        pass

    def run(self):
        ResultWriter.AddTheadInformation(i, "ThreadStarted;" + str(now()))
        if self.TestType == Config.TestType.System:
            self.FindWorkerIp()
        self.StartResourceThread()
        self.ConnectToSocket()
        self.CheckFogDeviceIsReady()
        self.StartOperation()

    def StartResourceThread(self):
        if FogTester.resource_threads.get(self.url) is not None:
            FogTester.resource_threads[self.url] = ResourceInformation(url+':'+self.ResourcePort)
            FogTester.resource_threads[self.url].start()
            ResultWriter.AddTheadInformation(i, "ResourceThreadStarted;" + str(now()))

    def FindWorkerIp(self):
        pass
    def ConnectToSocket(self):
        sio = socketio.Client()
        self.sio = sio

        @sio.on("connect")
        def connect():
            self.FogConnected = True
            ResultWriter.AddTheadInformation(self.i, "DeviceConnected;" + str(now()))
            # Send user index
            sio.emit("app_info", self.i)
            logger.info(self.i + " connected")

        @sio.on("application_disconnected")
        def application_disconnected(status):
            ResultWriter.AddTheadInformation(self.i, "ApplicationDisconnected;" + str(now()))
            self.err = True

        @sio.on("process_ready")
        def process_ready(status):
            if status:
                self.FogProcessIsReady = True
                ResultWriter.AddTheadInformation(i, "ProcessReady;" + str(now()))

            else:
                ResultWriter.AddTheadInformation(i, "ProcessCannotReady;" + str(now()))
                logger.error("Thread No: " + self.i + "faced an error. Message: " + info)
                sio.disconnect()
                self.err = True

        @sio.on("test")
        def test(info):
            print("Test message" + self.i)

        # Message -> 'data_index;result;added_queue;process_started;process_finished;response_time'
        @sio.on("result")
        def result(message):
            received_time = now()
            csvline = csv_line = "result;" + message + ";" + str(received_time)
            ResultWriter.AddThreadTimeInformation(self.i, csvline)
            res = result.split(";")
            data_index= int(res[0])
            if self.i == '0' and data_index % 50 == 0:
                for request_time in self.RequestTimeList:
                    if data_index == request_time[0]:
                        total_time = request_time[1] - received_time
                        new_info = 'remain: '+ res[0] + "/" + str(
                                self.Application.DataLength * Config.Configuration.SendAllDataTimes)+
                                "  -  TotalTime: "+str(total_time)+"  -  AddedQueue: "+res[2]+
                                "  -  ProcessStarted: " + res[3] + "  -  ProcessFinished: " + res[4] +
                                 "  -  ResponseTime: " + res[5]
                        logger.info(new_info)

        @sio.on('disconnected')
        def disconnected():
            logger.info(self.i + 'th User disconnected.')

        while True:
            try:
                # sio.connect('http://192.168.2.59:3000')
                sio.connect(self.url)
                sio.emit("temp", "kadir")
                break
            except Exception as e:
                logger.error(self.url + " connection err")
                time.sleep(1)

    def StopThread(self):
        FogTester.ClosedThreads += 1
        if FogTester.ClosedThreads >= FogTester.ThreadCount:
            print("Finished")
            os._exit(1)
        sys.exit()

    def CheckFogDeviceIsReady(self):
        logger.info(self.i + " wait device is ready!")

        while not self.FogProcessIsReady:
            if self.err:
                self.StopThread()

            time.sleep(0.2)

        logger.info(self.i + "th device is ready!")

    def SendData(self):
        if self.err:
            self.interval.stop()
            self.sio.disconnect()
            self.StopThread()

        data = self.Application.Data[self.data_index % self.Application.DataLength]

        self.data_index += 1

        # self.data_index = (self.data_index + 1) % self.Application.DataLength
        time_info = {'index': self.data_index, 'data_sent': now()}
        self.sio.emit("sensor_data", {'data': data, 'time_info': time_info})
        if self.data_index > self.Application.DataLength * Config.Configuration.SendAllDataTimes:
            self.interval.stop()
            self.StopThread()

    def StartOperation(self):
        self.interval = SetInterval(self.SamplingPeriod, self.SendData)


class ResourceInformation(Thread):
    def __init__(self, url):
        Thread.__init__(self)
        self.url = url

    def run(self):
        sio = socketio.Client()
        self.sio = sio

        @sio.on("connect")
        def connect():
            self.FogConnected = True
            sio.emit('register_resource', True)
            logger.info('Resource Information for ' + self.url + " connected")

        @sio.on("resource_info")
        def process_ready(info):
            ResultWriter.AddResourceInformation(self.url, info)

        @sio.on('disconnected')
        def disconnected():
            logger.info(self.i + 'th User disconnected.')

        while True:
            try:
                sio.connect(self.url)
                break
            except Exception as e:
                logger.error("Resource Information connection err")
                time.sleep(1)


def Main():
    rw = ResultWriter()

    index = 0
    for url, app_infos in Config.Configuration.Servers.items():
        for app in app_infos:
            for i in range(app['thread_count']):
                thread = FogTester(str(index), url, app['worker_port'], app['resource_port'], GaitAnalysis)
                thread.start()
                FogTester.threads.append(thread)
                index += 1

    FogTester.ThreadCount = len(threads)


if __name__ == "__main__":
    Main()
