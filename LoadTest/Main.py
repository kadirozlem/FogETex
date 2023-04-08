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
    Obj=None
    ThreadTimeInfo = {}
    ThreadInformations = {}
    ResourceInfo = {}

    def __init__(self):
        ResultWriter.Obj=self
        self.directory = Config.Configuration.FileDirectory + datetime.datetime.today().strftime(
            '%Y_%m_%d___%H_%M_%S') + Config.Configuration.FilePostfix + "/"
        os.makedirs(self.directory, exist_ok=True)
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
        timeInfo = ResultWriter.ThreadTimeInfo.get(thread_no)
        if timeInfo is None:
            ResultWriter.ThreadTimeInfo[thread_no] = [record + "\n"]
        else:
            timeInfo.append(record + "\n")

    @staticmethod
    def AddResourceInformation(url, info):
        resourceInfo = ResultWriter.ResourceInfo.get(url)
        if resourceInfo is None:
            ResultWriter.ResourceInfo[url] = [json.dumps(info) + "\n"]
        else:
            resourceInfo.append(json.dumps(info) + "\n")

    @staticmethod
    def AddThreadInformation(thread_no, record):
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
        self.Data = GaitAnalysis.GetData(self.i)
        self.TestType = test_type
        self.data_index = 0
        self.err = False
        self.RequestTimeList = []
        self.StopCriteria = self.Data.CalibrationLen + self.Data.TestDataLen * Config.Configuration.SendAllDataTimes
        ResultWriter.AddThreadInformation(i, "Feature;Value")
        ResultWriter.AddThreadInformation(i, "DeviceURL;" + self.Application.Name)
        ResultWriter.AddThreadInformation(i, "TestType;" + Config.TestType.getName(self.TestType))
        ResultWriter.AddThreadInformation(i, "DeviceURL;" + self.url)
        ResultWriter.AddThreadInformation(i, "ThreadIndex;" + self.i)
        ResultWriter.AddThreadInformation(i, "DataUserNo;" + self.Data.UserNo)
        ResultWriter.AddThreadInformation(i, "DataStepLength;" + self.Data.StepLength)
        ResultWriter.AddThreadInformation(i, "CalibrationDataLength;" + str(self.Data.CalibrationLen))
        ResultWriter.AddThreadInformation(i, "TestDataLength;" + str(self.Data.TestDataLen))
        ResultWriter.AddThreadInformation(i, "TestDataRepeatCount;" + str(Config.Configuration.SendAllDataTimes))
        ResultWriter.AddThreadInformation(i, "ThreadCreated;" + str(now()))
        pass

    def run(self):
        self.StartResourceThread()
        ResultWriter.AddThreadInformation(self.i, "ThreadStarted;" + str(now()))
        if self.TestType == Config.TestType.System:
            self.FindWorkerIp()
        self.ConnectToSocket()
        self.CheckFogDeviceIsReady()
        self.StartOperation()

    def StartResourceThread(self):
        if FogTester.resource_threads.get(self.url) is None:
            FogTester.resource_threads[self.url] = ResourceInformation(self.url + ':' + self.ResourcePort)
            FogTester.resource_threads[self.url].start()
            ResultWriter.AddThreadInformation(self.i, "ResourceThreadStarted;" + str(now()))

    def FindWorkerIp(self):
        pass

    def ConnectToSocket(self):
        sio = socketio.Client()
        self.sio = sio

        @sio.on("connect")
        def connect():
            self.FogConnected = True
            ResultWriter.AddThreadInformation(self.i, "DeviceConnected;" + str(now()))
            # Send user index
            sio.emit("app_info", self.i)
            logger.info(self.i + " connected")

        @sio.on("application_disconnected")
        def application_disconnected(status):
            ResultWriter.AddThreadInformation(self.i, "ApplicationDisconnected;" + str(now()))
            self.err = True

        @sio.on("process_ready")
        def process_ready(message):
            res = message.split(";")
            if int(res[0]):
                self.FogProcessIsReady = True
                ResultWriter.AddThreadInformation(self.i, "ProcessReady;" + str(now()))

            else:
                ResultWriter.AddThreadInformation(self.i, "ProcessCannotReady;" + str(now()))
                logger.error("Thread No: " + self.i + " faced an error. Message: "+res[1])
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
            res = message.split(";")
            data_index = int(res[0])
            if self.i == '0' and data_index % 50 == 0:
                for i in range(len(self.RequestTimeList)):
                    request_time = self.RequestTimeList[i]
                    if data_index == request_time[0]:
                        total_time =  received_time - request_time[1]
                        new_info = 'remain: ' + res[0] + "/" + str(
                            self.StopCriteria) + "  -  TotalTime: " + str(
                            total_time) + "  -  AddedQueue: " + res[2] + "  -  ProcessStarted: " + res[
                                       3] + "  -  ProcessFinished: " + res[4] + "  -  ResponseTime: " + res[5]
                        logger.info(new_info)
                        self.RequestTimeList.pop(i)
                        break
            if data_index == 0:
                ResultWriter.AddThreadInformation(self.i, "FirstResponseReceived;" + str(received_time))

        @sio.on('disconnected')
        def disconnected():
            ResultWriter.AddThreadInformation(self.i, "User disconnected;" + str(now()))
            logger.info(self.i + 'th User disconnected.')

        while True:
            try:
                # sio.connect('http://192.168.2.59:3000')
                sio.connect(self.url + ":" + self.WorkerPort)
                sio.emit("temp", "kadir")
                break
            except Exception as e:
                logger.error(self.url + " connection err")
                time.sleep(1)

    def StopThread(self):
        FogTester.ClosedThreads += 1
        ResultWriter.AddThreadInformation(self.i, "TheadStopped;" + str(now()))
        if FogTester.ClosedThreads >= FogTester.ThreadCount:
            ResultWriter.Obj.TimerEvent()
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
        message = None
        data_index = self.data_index
        if self.data_index < self.Data.CalibrationLen:
            message = str(data_index) + "|1;" + str(self.Data.CalibrationData[self.data_index])
        else:
            message = str(data_index) + "|0;" + str(
                self.Data.TestData[(self.data_index - self.Data.CalibrationLen) % self.Data.TestDataLen])

        self.data_index += 1

        request_time = now()
        self.sio.emit("sensor_data", message)

        csv_line = "request;" + str(data_index) + ";" + str(request_time)
        ResultWriter.AddThreadTimeInformation(self.i, csv_line)

        if self.i == '0' and data_index % 50 == 0:
            self.RequestTimeList.append((data_index, request_time))

        if self.data_index > self.StopCriteria:
            self.interval.stop()
            self.StopThread()

    def StartOperation(self):
        ResultWriter.AddThreadInformation(self.i, "FirstDataSent;" + str(now()))
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
    for url, app_info in Config.Configuration.Servers.items():
        for i in range(app_info['thread_count']):
            thread = FogTester(str(index), url, app_info['worker_port'], app_info['resource_port'], GaitAnalysis,
                               Config.Configuration.ApplicationTestType)
            thread.start()
            FogTester.threads.append(thread)
            index += 1

    FogTester.ThreadCount = len(FogTester.threads)


if __name__ == "__main__":
    Main()
