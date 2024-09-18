import json
import os
import re

import os
import statistics
from dataclasses import dataclass
import numpy as np

import pandas as pd
from scipy.signal import savgol_filter
# Import colorama
from colorama import init, Fore, Style

from FileOperations import FileOperations
from Charts import Charts
from Configuration import Configuration

# initialize
init()


class Print:
    ErrorBuffer = []

    @staticmethod
    def WriteErrors():
        while len(Print.ErrorBuffer) > 0:
            Print.Red(Print.ErrorBuffer.pop(0))

    @staticmethod
    def AddError(txt):
        Print.ErrorBuffer.append(txt)

    @staticmethod
    def Red(txt):
        print(Fore.RED + txt + Style.RESET_ALL)

    @staticmethod
    def White(txt):
        print(Fore.WHITE + txt + Style.RESET_ALL)

    @staticmethod
    def Blue(txt):
        print(Fore.BLUE + txt + Style.RESET_ALL)

    @staticmethod
    def Green(txt):
        print(Fore.GREEN + txt + Style.RESET_ALL)


class RequestTime:
    TotalResponseTime = []
    TotalResponseTimeHeaders = []

    def __init__(self, arr):
        self.index = arr[1]
        self.RequestTimestamp = float(arr[2])
        self.isWAN = False

    def AddResult(self, arr):
        self.Result = arr[2]
        self.AddedQueue = float(arr[3])
        self.ProcessStarted = float(arr[4])
        self.ProcessTime = float(arr[5])
        self.WorkerTotal = float(arr[6])
        self.ResponseTimestamp = float(arr[-1])
        self.TotalResponseTime = self.ResponseTimestamp - self.RequestTimestamp

        self.ResultReceivedSocket = self.WorkerTotal - (self.AddedQueue + self.ProcessStarted + self.ProcessTime)
        if len(arr) > 8:
            self.isWAN = True
            self.UserEmitterReqRes = float(arr[7])
            self.Network = (self.TotalResponseTime - self.UserEmitterReqRes) / 2
            self.UserEmitterToWorker = (self.UserEmitterReqRes - self.WorkerTotal) / 2
            self.Latency = self.Network + self.UserEmitterToWorker + self.AddedQueue
        else:
            self.Network = (self.TotalResponseTime - self.WorkerTotal) / 2
            self.Latency = self.Network + self.AddedQueue

        self.ExecutionTime = self.ProcessTime
        self.QueuingDelay = self.ProcessStarted
        self.ResponseTime = self.TotalResponseTime

        if self.Result != "-1" and self.TotalResponseTime < 0:
            a = 1

    def GetHeader(self):
        if self.isWAN:
            return [
                "UB",  # User Broker (User Emitter)
                "BS",  # Broker Socket (Worker)
                "SQ",  # Socket to Queue
                "QP",  # Queue Wait Time
                "PT",  # Process Time
                "PS",  # Process to Socket
                "SB",  # Socket Broker
                "BU"  # Broker User
            ]
        else:
            return [
                "US",  # User to Socket (Worker)
                "SQ",  # Socket to Queue
                "QP",  # Queue Wait Time
                "PT",  # Process Time
                "PS",  # Process to Socket
                "SB"  # Socket to User
            ]

    def GetValues(self):
        if self.isWAN:
            return [self.Network, self.UserEmitterToWorker, self.AddedQueue, self.ProcessStarted, self.ProcessTime,
                    self.ResultReceivedSocket, self.UserEmitterToWorker, self.Network]
        else:
            return [self.Network, self.AddedQueue, self.ProcessStarted, self.ProcessTime, self.ResultReceivedSocket,
                    self.Network]


class FogAnalysis:
    TestResults = {
    }

    @staticmethod
    def WriteTestResults(name="TestResults"):
        os.makedirs('./Cache/', exist_ok=True)
        json.dump(FogAnalysis.TestResults, open('./Cache/Stress_' + name + '.json', "w"))

    @staticmethod
    def ReloadTestResult(name="TestResults"):
        if os.path.exists('./Cache/Stress_' + name + '.json'):
            FogAnalysis.TestResults = json.load(open('./Cache/Stress_' + name + '.json'))
            return True
        return False

    @staticmethod
    def CheckFiles(functionName):
        print("StressTest Analysis Started.")

        functionName("/StressTest/")


    @staticmethod
    def CheckThreadInformationExists(directory):

        folders = FileOperations.GetFolders(directory)
        folder_count = len(folders)
        counter = 1
        for folder in folders:
            print(f"[{counter}/{folder_count}]: {folder}", end="\r")
            test_path = directory + folder
            files = FileOperations.GetFiles(test_path)
            TimeInformation = [x for x in files if x.endswith('.csv') and "ThreadInformation" in x]
            if len(TimeInformation) == 0:
                Print.Red(test_path)
            counter += 1

    @staticmethod
    def CheckTimeInformationExists(directory):
        folders = FileOperations.GetFolders(directory)
        folder_count = len(folders)
        counter = 1
        for folder in folders:
            print(f"[{counter}/{folder_count}]: {folder}", end="\r")
            test_path = directory + folder
            files = FileOperations.GetFiles(test_path)
            TimeInformation = [x for x in files if x.endswith('.csv') and "ThreadInformation" not in x]
            if len(TimeInformation) == 0:
                Print.Red(test_path)
            counter += 1

    @staticmethod
    def CheckTimeInformationSize(directory):
        limit = 17000

        not_res_limit = 200
        folders = FileOperations.GetFolders(directory)
        folder_count = len(folders)

        counter = 1
        for folder in folders:

            test_path = directory + folder
            files = FileOperations.GetFiles(test_path)
            TimeInformation = [x for x in files if x.endswith('.csv') and "ThreadInformation" not in x]
            if len(TimeInformation) != 0:
                responded_request, candidate_request, requests = FogAnalysis.ReadTimeInformationFile(test_path,
                                                                                                     TimeInformation[0])
                if responded_request < limit:
                    Print.AddError("Small file: " + str(responded_request) + "/" + str(limit))
                    Print.AddError("Path: " + test_path + "/" + TimeInformation[0])
                if candidate_request > not_res_limit:
                    Print.AddError("To much Non request file: " + str(candidate_request) + "/" + str(
                        candidate_request + responded_request))
                    Print.AddError("Path: " + test_path + "/" + TimeInformation[0])
            else:
                Print.AddError("Time information is not found " + test_path)
            if len(requests) > 0:
                write_directory = FileOperations.PreprocessedResults + test_path + "/"
                # requests = [x for x in requests if hasattr(x, 'Result')]
                print(f"[{counter}/{folder_count}]: Size: {len(requests)} -- {folder}")
                requests.sort(key=lambda x: x.index)
                header = requests[0].GetHeader()
                FileOperations.WriteDataToCSV([x.GetValues() for x in requests if x.Result == "-1"], header,
                                              write_directory, "calibration")
                FileOperations.WriteDataToCSV([x.GetValues() for x in requests if x.Result != "-1"], header,
                                              write_directory, "predict")
                FileOperations.WriteDataToCSV([x.GetValues() for x in requests], header, write_directory, "full")
            else:
                print(f"[{counter}/{folder_count}]: {folder}")

            counter += 1

    @staticmethod
    def ReadTimeInformationFile(directory, file):
        samples = FileOperations.ReadCSVFile(directory, file)
        candidate = {}
        requests = []

        for sample in samples:
            try:
                if sample[0] == "request":
                    candidate[sample[1]] = RequestTime(sample)
                else:
                    request = candidate.get(sample[1])
                    if request is None:
                        print("Response cannot found!")
                        print(directory + file + "    Index:" + sample[1])
                        print()
                    else:
                        request.AddResult(sample)
                        del candidate[sample[1]]
                    requests.append(request)
            except:
                pass

        return (len(requests), len(candidate), requests)

    @staticmethod
    def DrawTimeInformationEachTestGroup(directory):
        limit = 17000
        not_res_limit = 200
        folders = FileOperations.GetFolders(directory)
        folder_count = len(folders)

        counter = 1
        test_results = []
        labels = []
        for folder in folders:

            test_path = directory + folder
            files = FileOperations.GetFiles(test_path)
            TimeInformation = [x for x in files if x.endswith('.csv') and "ThreadInformation" not in x]
            if len(TimeInformation) != 0:
                responded_request, candidate_request, requests = FogAnalysis.ReadTimeInformationFile(test_path,
                                                                                                     TimeInformation[0])

            else:
                Print.AddError("Time information is not found " + test_path)
            if len(requests) > 0:
                # requests = [x for x in requests if hasattr(x, 'Result')]
                print(f"[{counter}/{folder_count}]: Size: {len(requests)} -- {folder}")
                requests.sort(key=lambda x: x.index)
                # header = requests[0].GetHeader()

                values = [x.TotalResponseTime for x in requests if x.Result != "-1"]
                test_results.append(values)
                labels.append(counter)
                # Print.AddError(str(len(values))+";"+test_path)
            else:
                print(f"[{counter}/{folder_count}]: {folder}")

            counter += 1

        write_directory = FileOperations.ProcessedResults + "GroupTimeInfo/"
        test_names = directory.replace('/Full/', "").split('/')
        Charts.BoxPlot(test_results, labels, "Sample number", "Total Time [s]", write_directory,
                       test_names[-2] + "_" + test_names[-1])

    @staticmethod
    def AddAllDataToDictionary(directory):
        limit = 17000
        not_res_limit = 200
        folders = FileOperations.GetFolders(directory)
        folder_count = len(folders)

        counter = 1

        test_results = []
        for folder in folders:
            splitted_name = folder.split("_")
            test_name = splitted_name[-1]
            device_name = splitted_name[-2]
            if FogAnalysis.TestResults.get(device_name) is None:
                FogAnalysis.TestResults[device_name] = {}
            if FogAnalysis.TestResults.get(device_name).get(test_name) is None:
                FogAnalysis.TestResults[device_name][test_name] = []
            test_path = directory + folder
            files = FileOperations.GetFiles(test_path)
            TimeInformation = [x for x in files if x.endswith('.csv') and "ThreadInformation" not in x]

            if len(TimeInformation) == int(test_name):
                for time_info in TimeInformation:
                    responded_request, candidate_request, requests = FogAnalysis.ReadTimeInformationFile(test_path,
                                                                                                     TimeInformation[0])

                    if len(requests) > 0:
                        print(f"[{counter}/{folder_count}]: Size: {len(requests)} -- {folder}-{time_info}")
                        requests.sort(key=lambda x: x.index)

                        values = [getattr(x, Configuration.AttributeName) * 1000 for x in requests if x.Result != "-1"][
                                 Configuration.StartIndex:Configuration.StartIndex + Configuration.FullDataSize]
                        FogAnalysis.TestResults[device_name][test_name].extend(values)
                    else:
                        print(f"[{counter}/{folder_count}]: {folder}")


            else:
                Print.AddError("Time information is not found " + test_path)
            counter += 1
    @staticmethod
    def ProcessResourceRecord(record, start_time):
        timestamp = record["timestamp"]
        process_time = timestamp - start_time if start_time is not None else 0
        cpu_usage = record["cpu_percentage"]["total"]["usage"]
        memory_usage = (record["totalmem"] - record["freemem"]) / record["totalmem"] * 100
        total_memory = record["totalmem"]
        rx = record["network_bandwidth"]["RX"]["Bytes"] / 1000 * 8
        tx = record["network_bandwidth"]["TX"]["Bytes"] / 1000 * 8
        bandwidth = rx + tx

        return [timestamp, process_time, cpu_usage, memory_usage, total_memory, rx, tx, bandwidth]

    @staticmethod
    def ReadResourceData(directory, filename=None):
        folders = FileOperations.GetFolders(directory)
        folder_count = len(folders)
        # Print.AddError(str(folder_count)+"  :"+directory)
        # return
        counter = 1
        test_results = []
        for folder in folders:
            if counter > Configuration.TestCount:
                break

            test_path = directory + folder
            files = FileOperations.GetFiles(test_path)

            ResourceInformation = [x for x in files if
                                   x.endswith('.json') and x.startswith("resource") and (
                                           filename is None or x == filename)]
            if len(ResourceInformation) != 0:
                headers = ['timestamp', 'ProcessTime', 'CPU_Usage', 'Memory_Usage', 'Total_Memory', 'RX', 'TX',
                           'Bandwidth']
                search_index = headers.index(Configuration.AttributeName)
                processed_records = []
                records = FileOperations.ReadJsonFile(test_path, ResourceInformation[0])
                start_time = None
                for record in records:
                    if start_time is None:
                        start_time = record['timestamp']
                    processed_record = FogAnalysis.ProcessResourceRecord(record, start_time)[search_index]

                    processed_records.append(processed_record)

                if len(processed_records) > 0:
                    print(f"[{counter}/{folder_count}]: Size: {len(processed_records)} -- {folder}")
                    test_results.extend(
                        processed_records[Configuration.ResourceStartIndex:Configuration.ResourceEndIndex])
                else:
                    print(f"[{counter}/{folder_count}]: {folder}")
                counter += 1


            else:
                Print.AddError("Resource information is not found " + test_path)
                counter += 1
        return test_results

    @staticmethod
    def AddAllResourceDataToDictionary():
        lte_worker_name = "resource__192_168_2_151_17796.json"
        lte_broker = "resource__http_212_253_104_215_17796_URL_192_168_2_151_17796.json"

        wifi_worker = "resource__http_192_168_2_151_17796.json"

        # LTE
        FogAnalysis.TestResults["MockClient"]["Worker_LTE"] = FogAnalysis.ReadResourceData("MockClient/LTE/Full/",
                                                                                           lte_worker_name)
        FogAnalysis.TestResults["MockClient"]["Broker_LTE"] = FogAnalysis.ReadResourceData("MockClient/LTE/Full/",
                                                                                           lte_broker)


        # WiFi
        FogAnalysis.TestResults["MockClient"]["WiFi"] = FogAnalysis.ReadResourceData(
            "MockClient/WiFi/Full/",
            wifi_worker)

        FogAnalysis.TestResults["MockClient"]["Worker_WiFi"] = FogAnalysis.ReadResourceData(
            "MockClient/Worker_WiFi/Full/")

        FogAnalysis.TestResults["MockClient"]["Broker_WiFi"] = FogAnalysis.ReadResourceData(
            "MockClient/Broker_WiFi/Full/")

        FogAnalysis.TestResults["MockClient"]["Cloud_WiFi"] = FogAnalysis.ReadResourceData(
            "MockClient/Cloud_WiFi/Full/")

        FogAnalysis.TestResults["MockClient"]["LTE_Cloud"] = FogAnalysis.ReadResourceData(
            "MockClient/LTE_Cloud/Full/")

    @staticmethod
    def AddArbitrationTimeToDictionary(directory):

        limit = 25

        folders = FileOperations.GetFolders(directory)

        counter = 1
        test_results = []
        for folder in folders:
            if counter > limit:
                break

            test_path = directory + folder
            files = FileOperations.GetFiles(test_path)
            ThreadInformation = [x for x in files if x.endswith('.csv') and "ThreadInformation" in x]
            if len(ThreadInformation) != 0:
                thread_infos = FileOperations.ReadCSVFile(test_path, ThreadInformation[0])
                thread_started = process_ready = None
                error= False
                for info in thread_infos:
                    if info[0] == "ThreadStarted":
                        thread_started = float(info[1])
                    if info[0] == "ProcessReady":
                        process_ready = float(info[1])
                        break
                    if info[0] =="SocketConnectError":
                        error =True
                        break
                if not error:
                    diff =process_ready - thread_started
                    test_results.append((diff) * 1000)
                    if diff>1:
                        a=1
                else:
                    Print.AddError("Thread information is not found " + test_path)

                counter += 1

        test_names = directory.replace('/Full/', "").replace('/Short/', "").split('/')

        if FogAnalysis.TestResults[test_names[-2]].get(test_names[-1]) is not None:
            FogAnalysis.TestResults[test_names[-2]][test_names[-1]].extend(test_results)

        else:
            FogAnalysis.TestResults[test_names[-2]][test_names[-1]]=test_results



    @staticmethod
    def PlotResponseTime():
        FogAnalysis.TestResults = {
            "ActualClient": {},
            "MockClient": {}
        }
        y_title = "Mean Response Time [ms]"
        directory = FileOperations.ProcessedResults + "ResponseTime/"
        filename = "ResponseTime"

        Configuration.AttributeName = filename

        if not FogAnalysis.ReloadTestResult(Configuration.AttributeName):
            FogAnalysis.CheckFiles(FogAnalysis.AddAllDataToDictionary)
            FogAnalysis.WriteTestResults(Configuration.AttributeName)

        ylim_box=(0,225)

        Charts.StressTestLines( FogAnalysis.TestResults, None, y_title, directory, filename + "_Mean_SimpleBox",
                                showBoxPlot=True, func=statistics.mean,ylim=ylim_box)

    @staticmethod
    def PlotExecutionTime():
        FogAnalysis.TestResults = {
            "ActualClient": {},
            "MockClient": {}
        }
        y_title = "Mean Execution Time [ms]"
        directory = FileOperations.ProcessedResults + "ExecutionTime/"
        filename = "ExecutionTime"

        Configuration.AttributeName = filename

        if not FogAnalysis.ReloadTestResult(Configuration.AttributeName):
            FogAnalysis.CheckFiles(FogAnalysis.AddAllDataToDictionary)
            FogAnalysis.WriteTestResults(Configuration.AttributeName)

        ylim_box = (0, 8)

        Charts.StressTestLines(FogAnalysis.TestResults, None, y_title, directory, filename + "_Mean_SimpleBox",
                                showBoxPlot=True, func=statistics.mean, ylim=ylim_box)

    @staticmethod
    def PlotLatencyTime():
        FogAnalysis.TestResults = {

        }
        y_title = "Mean Latency [ms]"
        directory = FileOperations.ProcessedResults + "Latency/"
        filename = "Latency"

        Configuration.AttributeName = filename

        if not FogAnalysis.ReloadTestResult(Configuration.AttributeName):
            FogAnalysis.CheckFiles(FogAnalysis.AddAllDataToDictionary)
            FogAnalysis.WriteTestResults(Configuration.AttributeName)

        ylim_box = (0, 120)

        Charts.StressTestLines(FogAnalysis.TestResults, None, y_title, directory, filename + "_Mean_SimpleBox",
                                showBoxPlot=True, func=statistics.mean, ylim=ylim_box)

    @staticmethod
    def PlotQueuingDelayTime():
        FogAnalysis.TestResults = {

        }
        y_title = "Mean Queuing Delay [ms]"
        directory = FileOperations.ProcessedResults + "QueuingDelay/"
        filename = "QueuingDelay"

        Configuration.AttributeName = filename

        if not FogAnalysis.ReloadTestResult(Configuration.AttributeName):
            FogAnalysis.CheckFiles(FogAnalysis.AddAllDataToDictionary)
            FogAnalysis.WriteTestResults(Configuration.AttributeName)

        ylim_box = (0,25)

        Charts.StressTestLines(FogAnalysis.TestResults, None, y_title, directory, filename + "_Mean_SimpleBox",
                                showBoxPlot=True, func=statistics.mean,ylim=ylim_box)

    @staticmethod
    def PlotJitter():
        FogAnalysis.TestResults = {

        }
        y_title = "Jitter [ms]"
        directory = FileOperations.ProcessedResults + "Jitter/"
        filename = "Jitter"

        Configuration.AttributeName = "ResponseTime"

        if not FogAnalysis.ReloadTestResult(Configuration.AttributeName):
            FogAnalysis.CheckFiles(FogAnalysis.AddAllDataToDictionary)
            FogAnalysis.WriteTestResults(Configuration.AttributeName)

        ylim = (0, 30)


        Charts.StressTestLines(FogAnalysis.TestResults, None, y_title, directory, filename + "_StdDev_Simple",
                                func=statistics.stdev, ylim=ylim,legend_loc='upper left')
    @staticmethod
    def PlotCPUMemory_Usage():
        FogAnalysis.TestResults = {

        }
        y_title = "Mean Usage [%]"
        directory = FileOperations.ProcessedResults + "CPU_Memory_Usage/"
        filename = "CPU_Usage"
        Configuration.AttributeName = filename

        if not FogAnalysis.ReloadTestResult(Configuration.AttributeName):
            FogAnalysis.AddAllResourceDataToDictionary()
            FogAnalysis.WriteTestResults(Configuration.AttributeName)
        CPU_Results = FogAnalysis.TestResults

        FogAnalysis.TestResults = {

        }
        filename = "Memory_Usage"
        Configuration.AttributeName = filename
        if not FogAnalysis.ReloadTestResult(Configuration.AttributeName):
            FogAnalysis.AddAllResourceDataToDictionary()
            FogAnalysis.WriteTestResults(Configuration.AttributeName)
        Memory_Results = FogAnalysis.TestResults

        filename = "CPU_Memory_Usage"

        ylim_box = (0, 30)

        Charts.StressTestLines(CPU_Results, Memory_Results, None, y_title, directory, filename + "_Mean_SimpleBox",
                                showBoxPlot=True, func=statistics.mean, ylim=ylim_box)


    @staticmethod
    def Plot_Bandwidth():
        FogAnalysis.TestResults = {

        }
        y_title = "Mean Bandwidth [kbps]"
        directory = FileOperations.ProcessedResults + "Bandwidth/"
        filename = "Bandwidth"

        Configuration.AttributeName = filename

        if not FogAnalysis.ReloadTestResult(Configuration.AttributeName):
            FogAnalysis.AddAllResourceDataToDictionary()
            FogAnalysis.WriteTestResults(Configuration.AttributeName)

        ylim = (0, 1400)

        Charts.Resource_GroupedBox_Simple(FogAnalysis.TestResults, None, y_title, directory,
                                          filename + "_Simple_Mean_Box",
                                          showBoxPlot=True, func=statistics.mean,ylim=ylim)

    @staticmethod
    def PlotArbitrationTime():
        FogAnalysis.TestResults = {

        }
        y_title = "Mean Arbitration Time [ms]"
        directory = FileOperations.ProcessedResults + "ArbitrationTime/"
        filename = "ArbitrationTime"

        Configuration.AttributeName = filename

        if not FogAnalysis.ReloadTestResult(Configuration.AttributeName):
            FogAnalysis.CheckFiles(FogAnalysis.AddArbitrationTimeToDictionary,full=False, short=True)
            FogAnalysis.WriteTestResults(Configuration.AttributeName)

        ylim_box = (0,1000)

        Charts.StressTestLines(FogAnalysis.TestResults, None, y_title, directory, filename + "_Mean_SimpleBoxFull",
                                     showBoxPlot=True, func=statistics.mean,ylim=ylim_box)


    @staticmethod
    def CheckTimeValues(directory='/StressTest/'):
        limit = 17000
        not_res_limit = 200
        folders = FileOperations.GetFolders(directory)
        folder_count = len(folders)

        counter = 1

        folder_results_header =["DeviceName","TestName","Folder","TotalSize","TotalTestSize",
                         "MinLatency","MaxLatency","MeanLatency","StdLatency",
                         "MinQueuingDelay","MaxQueuingDelay","MeanQueueingDelay","StdQueueingDelay",
                         "MinExecutionTime","MaxExecutionTime","MeanExecutionTime","StdExecutionTime",
                         "MinResponseTime","MaxResponseTime","MeanResponseTime","StdResponseTime"]
        file_results_header = ["DeviceName","TestName","ThreadName","Folder","TotalSize","TotalTestSize",
                         "MinLatency","MaxLatency","MeanLatency","StdLatency",
                         "MinQueuingDelay","MaxQueuingDelay","MeanQueueingDelay","StdQueueingDelay",
                         "MinExecutionTime","MaxExecutionTime","MeanExecutionTime","StdExecutionTime",
                         "MinResponseTime","MaxResponseTime","MeanResponseTime","StdResponseTime"]

        folder_results = []
        file_results = []
        for folder in folders:
            splitted_name = folder.split("_")
            test_name = splitted_name[-1]
            device_name = splitted_name[-2]
            if FogAnalysis.TestResults.get(device_name) is None:
                FogAnalysis.TestResults[device_name] = {}
            if FogAnalysis.TestResults.get(device_name).get(test_name) is None:
                FogAnalysis.TestResults[device_name][test_name] = []
            test_path = directory + folder
            files = FileOperations.GetFiles(test_path)
            TimeInformation = [x for x in files if x.endswith('.csv') and "ThreadInformation" not in x]

            if len(TimeInformation) == int(test_name):
                latency_arr = []
                queuing_delay_arr = []
                execution_times_arr=[]
                response_times_arr=[]
                total_size = 0
                total_test_size = 0
                for time_info in TimeInformation:
                    responded_request, candidate_request, requests = FogAnalysis.ReadTimeInformationFile(test_path,
                                                                                                     TimeInformation[0])

                    if len(requests) > 0:
                        print(f"[{counter}/{folder_count}]: Size: {len(requests)} -- {folder}-{time_info}")
                        requests.sort(key=lambda x: x.index)

                        values = [x for x in requests if x.Result != "-1"][
                                 Configuration.StartIndex:Configuration.StartIndex + Configuration.FullDataSize]

                        latency = [x.Latency*1000 for x in values]
                        min_latency = min(latency)
                        max_latency = max(latency)
                        mean_latency = statistics.mean(latency)
                        std_latency = statistics.stdev(latency)
                        latency_arr.extend(latency)

                        queuing_delay= [x.QueuingDelay*1000 for x in values]
                        min_queuing_delay = min(queuing_delay)
                        max_queuing_delay = max(queuing_delay)
                        mean_queuing_delay = statistics.mean(queuing_delay)
                        std_queuing_delay = statistics.stdev(queuing_delay)
                        queuing_delay_arr.extend(queuing_delay)


                        execution_times = [x.ExecutionTime*1000 for x in values]
                        min_execution_time = min(execution_times)
                        max_execution_time = max(execution_times)
                        mean_execution_time = statistics.mean(execution_times)
                        std_execution_time = statistics.stdev(execution_times)
                        execution_times_arr.extend(execution_times)

                        response_time = [x.ResponseTime*1000 for x in values]
                        min_response_time = min(response_time)
                        max_response_time = max(response_time)
                        mean_response_time = statistics.mean(response_time)
                        std_response_time = statistics.stdev(response_time)
                        response_times_arr.extend(response_time)

                        size = len(requests)
                        total_size += size

                        test_size = len(values)
                        total_test_size += test_size

                        file_result = [device_name, test_name, time_info.replace(".csv",""), folder, str(size), str(test_size),
                            min_latency, max_latency, mean_latency, std_latency,
                            min_queuing_delay, max_queuing_delay, mean_queuing_delay, std_queuing_delay,
                            min_execution_time, max_execution_time, mean_execution_time, std_execution_time,
                            min_response_time, max_response_time, mean_response_time, std_response_time]
                        file_results.append(file_result)
                    else:
                        print(f"[{counter}/{folder_count}]: {folder}")





                min_latency = min(latency_arr)
                max_latency = max(latency_arr)
                mean_latency = statistics.mean(latency_arr)
                std_latency = statistics.stdev(latency_arr)

                min_queuing_delay = min(queuing_delay_arr)
                max_queuing_delay = max(queuing_delay_arr)
                mean_queuing_delay = statistics.mean(queuing_delay_arr)
                std_queuing_delay = statistics.stdev(queuing_delay_arr)

                min_execution_time = min(execution_times_arr)
                max_execution_time = max(execution_times_arr)
                mean_execution_time = statistics.mean(execution_times_arr)
                std_execution_time = statistics.stdev(execution_times_arr)

                min_response_time = min(response_times_arr)
                max_response_time = max(response_times_arr)
                mean_response_time = statistics.mean(response_times_arr)
                std_response_time = statistics.stdev(response_times_arr)


                folder_result = [device_name, test_name,folder, str(total_size), str(total_test_size),
                               min_latency, max_latency, mean_latency, std_latency,
                               min_queuing_delay, max_queuing_delay, mean_queuing_delay, std_queuing_delay,
                               min_execution_time, max_execution_time, mean_execution_time, std_execution_time,
                               min_response_time, max_response_time, mean_response_time, std_response_time]
                folder_results.append(folder_result)



            else:
                Print.AddError("Time information is not found " + test_path)
            counter += 1
        file_results.sort(key=lambda x: (x[0],int(x[1]),x[3],int(x[2])))
        folder_results.sort(key=lambda x: (x[0],int(x[1]),x[2]))
        FileOperations.WriteDataToCSV(file_results,file_results_header,"./StressTestResults/","FileResults")
        FileOperations.WriteDataToCSV(folder_results,folder_results_header,"./StressTestResults/","FolderResults")

if __name__ == '__main__':
    #FogAnalysis.CheckTimeValues()
    # FogAnalysis.CheckFiles(FogAnalysis.CheckTimeInformationExists)
    # FogAnalysis.CheckFiles(FogAnalysis.CheckThreadInformationExists)
    # FogAnalysis.CheckFiles(FogAnalysis.CheckTimeInformationSize)
    # FogAnalysis.CheckFiles(FogAnalysis.DrawTimeInformationEachTestGroup)
    # Configuration.AttributeName="CPU_Usage"
    # FogAnalysis.AddAllResourceDataToDictionary()
    # if not FogAnalysis.ReloadTestResult():
    #     FogAnalysis.CheckFiles(FogAnalysis.AddAllDataToDictionary, short=False)
    #     FogAnalysis.WriteTestResults()
    #FogAnalysis.PlotLatencyTime()
    #FogAnalysis.PlotExecutionTime()
    #FogAnalysis.PlotQueuingDelayTime()
    FogAnalysis.PlotResponseTime()
    #FogAnalysis.PlotJitter()
    #FogAnalysis.Plot_Bandwidth()
    #FogAnalysis.PlotArbitrationTime()
    #FogAnalysis.PlotCPUMemory_Usage()

    Print.WriteErrors()
