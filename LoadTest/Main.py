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
from Config import *
import requests
import geocoder
import re

GaitAnalysis.ReadAllData()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def now():
    return datetime.datetime.now().timestamp()


class SetInterval:
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
    Obj = None
    ThreadTimeInfo = {}
    ThreadInformations = {}
    ResourceInfo = {}

    def __init__(self):
        ResultWriter.Obj = self
        self.directory = Configuration.FileDirectory + datetime.datetime.today().strftime(
            '%Y_%m_%d___%H_%M_%S') + Configuration.FilePostfix + "/"
        os.makedirs(self.directory, exist_ok=True)
        self.timer = SetInterval(Configuration.FileWritePeriod, self.TimerEvent)

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
            filename = self.directory + "resource__" + re.sub('[^0-9a-zA-Z]+', '_', i) + ".json"
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
    Latitude = ''
    Longitude = ''

    def __init__(self, i, server, application, test_type):
        Thread.__init__(self)
        self.i = i
        self.Server = server
        self.SamplingPeriod = Configuration.SamplingPeriod
        self.FogProcessIsReady = False
        self.FogConnected = False
        self.Application = application
        self.Data = GaitAnalysis.GetData(self.i)
        self.TestType = test_type
        self.data_index = 0
        self.err = False
        self.RequestTimeList = []
        self.FileName = None
        self.StopCriteria = self.Data.CalibrationLen + self.Data.TestDataLen * Configuration.SendAllDataTimes
        ResultWriter.AddThreadInformation(i, "Feature;Value")
        ResultWriter.AddThreadInformation(i, "ApplicationName;" + self.Application.Name)
        ResultWriter.AddThreadInformation(i, "TestType;" + TestType.getName(self.TestType))
        ResultWriter.AddThreadInformation(i, "DeviceURL;" + self.Server.GetWorkerURL())
        ResultWriter.AddThreadInformation(i, "ThreadIndex;" + self.i)
        ResultWriter.AddThreadInformation(i, "DataUserNo;" + self.Data.UserNo)
        ResultWriter.AddThreadInformation(i, "DataStepLength;" + self.Data.StepLength)
        ResultWriter.AddThreadInformation(i, "CalibrationDataLength;" + str(self.Data.CalibrationLen))
        ResultWriter.AddThreadInformation(i, "TestDataLength;" + str(self.Data.TestDataLen))
        ResultWriter.AddThreadInformation(i, "TestDataRepeatCount;" + str(Configuration.SendAllDataTimes))
        ResultWriter.AddThreadInformation(i, "ThreadCreated;" + str(now()))


    def run(self):
        ResultWriter.AddThreadInformation(self.i, "ThreadStarted;" + str(now()))
        if self.TestType == TestType.System:
            self.AssignFogNode(self.Server.AssignFogNode_URL())
        self.StartResourceThread()
        self.ConnectToSocket()
        self.CheckFogDeviceIsReady()
        self.StartOperation()

    def StartResourceThread(self):
        if self.err:
            return
        if FogTester.resource_threads.get(self.Server.IP) is None:
            FogTester.resource_threads[self.Server.IP] = ResourceInformation(self.Server)
            FogTester.resource_threads[self.Server.IP].start()
            ResultWriter.AddThreadInformation(self.i, "ResourceThreadStarted;" + str(now()))

    def AssignFogNode(self, CloudUrl):
        url = CloudUrl + "?lat={}&lon={}".format(FogTester.Latitude, FogTester.Longitude)
        ResultWriter.AddThreadInformation(self.i, "AssignFogNode_Latitude;" + FogTester.Latitude)
        ResultWriter.AddThreadInformation(self.i, "AssignFogNode_Longitude;" + FogTester.Longitude)
        try:
            response = requests.get(url)
            assigned_time = str(now())
            response_json = response.json()
            error = response_json.get("err")
            if (error is not None):
                ResultWriter.AddThreadInformation(self.i, "AssignFogNode_Err:" + error + ";" + assigned_time)
                logger.error("Thread No: " + self.i + " faced an error at AssignFogNode. Message: " + error)
                self.StopThread(err=True)
            else:
                brokerIp = response_json.get("IP")
                brokerType = response_json.get("type")
                self.Server.BrokerIP = brokerIp
                ResultWriter.AddThreadInformation(self.i, "BrokerIPAssigned:" + assigned_time)
                ResultWriter.AddThreadInformation(self.i, "BrokerIP:" + brokerIp)
                ResultWriter.AddThreadInformation(self.i, "BrokerType:" + brokerType)
                distance = response_json.get("distance")
                ResultWriter.AddThreadInformation(self.i, "BrokerDistance:" + str(distance))
                logger.info("Broker IP: "+brokerIp+" - Type: "+brokerType)
                self.Server.IsWANDevice = brokerType == "WAN"
                self.AssignWorkerDevice(brokerIp)
        except Exception as err:
            ResultWriter.AddThreadInformation(self.i, "AssignFogNode_Err:CloudConnectionFailed;" + str(now()))
            logger.error("Thread No: " + self.i + " faced an error at AssignFogNode. Message: " + str(err))
            self.StopThread(err=True)

    def AssignWorkerDevice(self, brokerIp):
        try:
            response = requests.get(self.Server.AssignWorkerDevice_URL(brokerIp))
            assigned_time = str(now())
            response_json = response.json()
            error = response_json.get("err")
            if (error is not None):
                ResultWriter.AddThreadInformation(self.i, "AssignWorkerDevice_Err:" + error + ";" + assigned_time)
                logger.error("Thread No: " + self.i + " faced an error at AssignWorkerDevice. Message: " + error)
                self.StopThread(err=True)
            else:
                workerIP = response_json.get("IP")
                cpuUsage=response_json.get("CPU_Usage")
                self.Server.WorkerIP = workerIP
                logger.info("Worker Ip:" +workerIP)
                ResultWriter.AddThreadInformation(self.i, "WorkerDeviceAssigned:" + assigned_time)
                ResultWriter.AddThreadInformation(self.i, "WorkerIP:" + brokerIp)
                ResultWriter.AddThreadInformation(self.i, "CPU_Usage:" + str(cpuUsage))
                if self.Server.IsWANDevice:
                    self.Server.IP  = self.Server.BrokerIP
                else:
                    self.Server.IP  = self.Server.WorkerIP

        except Exception as err:
            ResultWriter.AddThreadInformation(self.i, "AssignWorkerDevice_Err:BrokerConnectionFailed;" + str(now()))
            logger.error("Thread No: " + self.i + " faced an error at AssignWorkerDevice. Message: " + str(err))
            self.StopThread(err=True)

    def ConnectToSocket(self):
        if self.err:
            return
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
                logger.error("Thread No: " + self.i + " faced an error. Message: " + res[1])
                sio.disconnect()
                self.StopThread(err=True)
                self.err = True

        @sio.on("test")
        def test(info):
            print("Test message" + self.i)

        # Message -> 'data_index;result;added_queue;process_started;process_finished;response_time'
        @sio.on("result")
        def result(message):
            received_time = now()
            csvline = "result;" + message + ";" + str(received_time)
            ResultWriter.AddThreadTimeInformation(self.i, csvline)
            res = message.split(";")
            data_index = int(res[0])
            if self.i == '0' and data_index % 50 == 0:
                for i in range(len(self.RequestTimeList)):
                    request_time = self.RequestTimeList[i]
                    if data_index == request_time[0]:
                        total_time = received_time - request_time[1]
                        new_info = 'remain: ' + res[0] + "/" + str(
                            self.StopCriteria) + "  -  TotalTime: " + str(
                            total_time) + "  -  AddedQueue: " + res[2] + "  -  ProcessStarted: " + res[
                                       3] + "  -  ProcessFinished: " + res[4] + "  -  ResponseTime: " + res[5]
                        logger.info(new_info)
                        self.RequestTimeList.pop(i)
                        break
            if data_index == 0:
                ResultWriter.AddThreadInformation(self.i, "FirstResponseReceived;" + str(received_time))

        @sio.on('filename')
        def filename(file):
            self.filename = file

            ResultWriter.AddThreadInformation(self.i, "Filename;" + self.filename)

        @sio.on('disconnected')
        def disconnected():
            ResultWriter.AddThreadInformation(self.i, "SocketDisconnected;" + str(now()))
            logger.info(self.i + 'th User disconnected.')

        while True:
            try:
                # sio.connect('http://192.168.2.59:3000')
                sio.connect(self.Server.GetSocketUrl(self.Server.IP, self.Server.IsWANDevice))
                sio.emit("temp", "kadir")
                break
            except Exception as e:
                logger.error(self.url + " connection err")
                time.sleep(1)

    def StopThread(self, err = False):
        FogTester.ClosedThreads += 1
        ResultWriter.AddThreadInformation(self.i, "TheadStopped;" + str(now()))
        self.err=True
        # if FogTester.ClosedThreads >= FogTester.ThreadCount:
        #     ResultWriter.Obj.TimerEvent()
        #     print("Finished")
        #     os._exit(1)
        #
        # sys.exit()
        if not err:
            Timer(Configuration.FileWritePeriod, self.SaveRequestFile).start()

    def SaveRequestFile(self):
        r = requests.get(self.Server.GetSocketUrl(self.Server.IP,False) + "/GetUserPackage?filename=" + self.filename)
        with open(ResultWriter.Obj.directory + self.filename, 'wb') as f:
            f.write(r.content)

        if FogTester.ClosedThreads >= FogTester.ThreadCount:
            ResultWriter.Obj.TimerEvent()
            print("Finished")
            os._exit(1)

        sys.exit()

    def CheckFogDeviceIsReady(self):
        if self.err:
            return
        logger.info(self.i + " wait device is ready!")

        while not self.FogProcessIsReady:
            if self.err:
                self.StopThread(err=True)

            time.sleep(0.2)

        logger.info(self.i + "th device is ready!")

    def SendData(self):
        if self.err:
            self.interval.stop()
            self.sio.disconnect()
            self.StopThread()
        message = None
        data_index = self.data_index
        self.data_index += 1

        if data_index < self.Data.CalibrationLen:
            message = str(data_index) + "|1;" + str(self.Data.CalibrationData[data_index])
        else:
            message = str(data_index) + "|0;" + str(
                self.Data.TestData[(self.data_index - self.Data.CalibrationLen) % self.Data.TestDataLen])


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
        if self.err:
            return
        ResultWriter.AddThreadInformation(self.i, "FirstDataSent;" + str(now()))
        self.interval = SetInterval(self.SamplingPeriod, self.SendData)


class ResourceInformation(Thread):
    def __init__(self, server):
        Thread.__init__(self)
        self.Server = server

        self.url = self.Server.GetResourceUrl(self.Server.IsWANDevice)
        if self.Server.IsWANDevice:
            self.worker_url = self.url.split("?URL=")[1]


    def run(self):
        sio = socketio.Client()
        self.sio = sio

        @sio.on("connect")
        def connect():
            self.FogConnected = True
            sio.emit('register_resource', True)
            logger.info('Resource Information for ' + self.url + " connected")

        @sio.on("resource_info")
        def resource_info(info):
            ResultWriter.AddResourceInformation(self.url, info)

        @sio.on("worker_info")
        def worker_info(info):
            ResultWriter.AddResourceInformation(self.worker_url, info)

        @sio.on("worker_connected")
        def worker_connected(info):
            logger.info('Resource Information for ' + self.worker_url + " connected")

        @sio.on("worker_connect_error")
        def worker_connect_error(info):
            logger.info('Resource Information for ' + self.worker_url + " connection error!")

        @sio.on("worker_disconnected")
        def worker_disconnected(info):
            logger.info('Resource Information for ' + self.worker_url + " disconnected")

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
    g = geocoder.ip('me')
    FogTester.Latitude, FogTester.Longitude = [str(x) for x in g.latlng]
    index = 0
    for server in Configuration.Servers:
        for i in range(server.ThreadCount):
            thread = FogTester(str(index), server, GaitAnalysis, Configuration.ApplicationTestType)
            thread.start()
            FogTester.threads.append(thread)
            index += 1

    FogTester.ThreadCount = len(FogTester.threads)


if __name__ == "__main__":
    Main()
