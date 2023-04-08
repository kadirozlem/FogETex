from enum import Enum


class TestType(Enum):
    Cloud= 1  # Start test for cloud
    Broker= 2  # Start test for broker
    Worker= 3  # Start test for worker
    System= 4  # Start test with finding IP from cloud and continue with Worker test.

    def getName(test_type):
        if test_type == TestType.Cloud:
            return "Cloud"
        if test_type == TestType.Broker:
            return "Broker"
        if test_type == TestType.Worker:
            return "Worker"
        if test_type == TestType.System:
            return "System"


class Configuration:
    SendAllDataTimes = 9
    FileWritePeriod = 5
    SamplingPeriod = 0.020
    FileDirectory = "./Results/"
    FilePostfix = "FogEtex"
    ApplicationTestType = TestType.Worker
    Servers = {

        'http://localhost': {'worker_port': '27592', 'resource_port': '17796', 'thread_count': 1}
    }
