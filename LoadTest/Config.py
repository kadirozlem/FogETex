from enum import Enum
from dataclasses import dataclass


class ServerInformation:
    def __init__(self, ip, worker_port, resource_port, thread_count, is_secure):
        self.CloudIP = ''
        self.BrokerIP = ''
        self.WorkerIP = ''
        self.IP = ip
        self.WorkerPort = worker_port
        self.ResourcePort = resource_port
        self.ThreadCount = thread_count
        self.IsSecure = is_secure
        self.IsWANDevice = False

        if Configuration.ApplicationTestType == TestType.Broker:
            self.BrokerIP = self.IP
        elif Configuration.ApplicationTestType == TestType.Worker:
            self.WorkerIP = self.IP
        else:  # Cloud or System
            self.CloudIP = self.IP

    def GetWorkerURL(self):
        return self.GetURLScheme() + self.IP + ":" + self.WorkerPort

    def GetResourceUrl(self, isWANDevice=False):
        return self.GetURLScheme() + self.IP + ":" + self.ResourcePort+("?URL="+self.WorkerIP+":"+self.ResourcePort if isWANDevice else "")

    def GetURLScheme(self):
        if self.IsSecure:
            return "https://"
        return "http://"

    # Cloud
    def AssignFogNode_URL(self):
        return self.GetURLScheme() + self.CloudIP + ":" + self.WorkerPort + "/Cloud/AssignFogNode"

    # Broker
    def AssignWorkerDevice_URL(self, brokerIp):
        return self.GetURLScheme() + brokerIp + ":" + self.WorkerPort + "/Broker/AssignWorkerDevice"

    # Socket URL
    def GetSocketUrl(self, ip, isWANDevice=False):
        return self.GetURLScheme() + ip + ":" + self.WorkerPort + ("?DeviceType=6&URL="+self.WorkerIP+":"+self.WorkerPort if isWANDevice else "")

    def GetUserPackage(self, ip, filename):
        return self.GetURLScheme() + ip + ":" + self.WorkerPort + "/GetUserPackage?filename=" + filename


class TestType(Enum):
    Cloud = 1  # Start test for cloud
    Broker = 2  # Start test for broker
    Worker = 3  # Start test for worker
    System = 4  # Start test with finding IP from cloud and continue with Worker test.

    def getName(test_type):
        if test_type == TestType.Cloud:
            return "Cloud"
        if test_type == TestType.Broker:
            return "Broker"
        if test_type == TestType.Worker:
            return "Worker"
        if test_type == TestType.System:
            return "System"


@dataclass
class Configuration:
    SendAllDataTimes = 1
    FileWritePeriod = 5
    SamplingPeriod = 0.020
    FileDirectory = "./Results/"
    FilePostfix = "FogEtex"
    ApplicationTestType = TestType.System


Configuration.Servers = [
    ServerInformation(ip='164.92.168.129', worker_port='27592', resource_port='17796', thread_count=1, is_secure=False)
]
