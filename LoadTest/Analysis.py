import json
import os
import re

import os
from dataclasses import dataclass
import numpy as np

import matplotlib.pyplot as plt
import pandas as pd
from scipy.signal import savgol_filter
import matplotlib as mpl

font = {'family': "Times New Roman",
        'weight': 'normal',
        'size': 8}

mpl.rc('font', **font)

mpl.rcParams['figure.dpi'] = 600
cm = 1 / 2.54
plt.rcParams["figure.figsize"] = (12 * cm, 10 * cm)
# plt.rcParams["figure.figsize"] = (16 * cm, 4 * cm)

plt.rcParams.update({'mathtext.default': 'regular'})


class Configuration:
    Save = True
    Colors = ["blue", "red", "black", "magenta"]


class FileOperations:
    ResultDirectory = './Results/'
    ProcessedResults = './ProcessedResults/'

    @staticmethod
    def GetResultsDirectoryNames():
        result_lists = os.listdir(FileOperations.ResultDirectory)
        procesed_lists = os.listdir(FileOperations.ProcessedResults)

        non_processed_lists = [x for x in result_lists if x not in procesed_lists]
        return non_processed_lists

    @staticmethod
    def GetFiles(directory):
        files = os.listdir(FileOperations.ResultDirectory + directory)
        return files

    @staticmethod
    def CreateFolder(directory):
        os.mkdir(FileOperations.ProcessedResults + directory)

    @staticmethod
    def CreateFolderIfNotExists(directory):
        if not os.path.exists(directory):
            os.mkdir(directory)

    @staticmethod
    def ReadJsonFile(directory, filename):
        with open(FileOperations.ResultDirectory + directory + "/" + filename) as file:
            lines = file.readlines()
            return [json.loads(x) for x in lines]

    @staticmethod
    def ReadCSVFile(directory, filename):
        with open(FileOperations.ResultDirectory + directory + "/" + filename) as file:
            lines = file.readlines()
            return [re.split(";|:", x) for x in lines]

    @staticmethod
    def WriteLines(directory, filename,lines):
        os.makedirs(directory, exist_ok=True)
        with open(directory +filename, 'a') as file:
            file.writelines(lines)

class RequestTime:
    TotalResponseTime = []
    TotalResponseTimeHeaders=[]

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
        self.ResultReceivedSocket = self.WorkerTotal-(self.AddedQueue+self.ProcessStarted+self.ProcessTime)
        if len(arr) > 8:
            self.isWAN =True
            self.UserEmitterReqRes = float(arr[7])
            self.Network = (self.TotalResponseTime - self.UserEmitterReqRes)/2
            self.UserEmitterToWorker = (self.UserEmitterReqRes-self.WorkerTotal)/2
        else:
            self.Network = (self.TotalResponseTime-self.WorkerTotal)/2

        if self.Result!="-1" and self.TotalResponseTime<0:
            a=1

    def GetHeader(self):
        if self.isWAN:
            return [
                "UB", #User Broker (User Emitter)
                "BS", #Broker Socket (Worker)
                "SQ", #Socket to Queue
                "QP", #Queue Wait Time
                "PT", #Process Time
                "PS", #Process to Socket
                "SB", #Socket Broker
                "BU" #Broker User
            ]
        else:
            return [
                "US", #User to Socket (Worker)
                "SQ", #Socket to Queue
                "QP", #Queue Wait Time
                "PT", #Process Time
                "PS", #Process to Socket
                "SB" #Socket to User
            ]

    def GetValues(self):
        if self.isWAN:
            return [self.Network, self.UserEmitterToWorker, self.AddedQueue, self.ProcessStarted, self.ProcessTime, self.ResultReceivedSocket, self.UserEmitterToWorker, self.Network]
        else:
            return [self.Network,self.AddedQueue, self.ProcessStarted, self.ProcessTime, self.ResultReceivedSocket, self.Network]

    def GetValues(self):
        if self.isWAN:
            return [ self.Network, self.UserEmitterToWorker,self.AddedQueue, self.ProcessStarted, self.ProcessTime, self.ResultReceivedSocket, self.UserEmitterToWorker, self.Network]
        else:
            return [self.Network,self.AddedQueue, self.ProcessStarted, self.ProcessTime, self.ResultReceivedSocket, self.Network]



class Results:
    Groups = {}

    def __init__(self, directory):
        self.directory = directory
        self.GroupName = self.directory[21:]
        self.AddGroup()
        self.Files = FileOperations.GetFiles(self.directory)
        # self.AnalysisRequestResponseCount()
        # self.AnalysisRequestResponseTime()
        self.AnalysisResourceFiles()


    def AddGroup(self):
        if Results.Groups.get(self.GroupName) is None:
            Results.Groups[self.GroupName] = [self]
        else:
            Results.Groups[self.GroupName].append(self)

    def AnalysisRequestResponseTime(self):
        requestResponseTimeFiles = [x for x in self.Files if
                                    x.endswith(".csv") and not x.endswith("ThreadInformation.csv")]
        for file in requestResponseTimeFiles:
            try:
                filename = file.replace(".csv","")
                samples = FileOperations.ReadCSVFile(self.directory, file)
                requests = [RequestTime(x) for x in samples if x[0] == "request"]
                for sample in samples:
                    if sample[0] == "result":
                        request = next((x for x in requests if x.index == sample[1]), None)
                        if request is None:
                            print("Response cannot found!")
                            print(self.directory + file + "    Index:" + sample[1])
                            print()
                        else:
                            request.AddResult(sample)
                requests.sort(key=lambda x:x.index)
                directory = FileOperations.ProcessedResults + self.directory + "/" + filename
                Results.PlotRequestResponseTime([x for x in requests if x.Result=="-1"], directory+"_calibration/", "work_time")
                Results.PlotRequestResponseTime([x for x in requests if x.Result!="-1"], directory+"_predict/", "work_time")
                Results.PlotRequestResponseTime(requests, directory+"_full/", "work_time")

                RequestTime.TotalResponseTime.append([x.TotalResponseTime for x in requests if x.Result!="-1"])
                RequestTime.TotalResponseTimeHeaders.append(self.GroupName+"_"+filename)
            except Exception as err:
                print("Error Request Response Time: " + self.directory + "/" + file)
                print(err)
                print()

    @staticmethod
    def PlotRequestResponseTime(requests, directory, filename):
            req_res_times = [x.GetValues() for x in requests]
            transposed_val = (np.array(req_res_times)*1000).transpose().tolist()

            req_res_header = requests[0].GetHeader()

            x_title = "Data Transfer"
            y_title = "Duration [ms]"
            Results.BoxPlot(transposed_val, req_res_header,x_title,y_title,directory, filename)


    @staticmethod
    def TotalRequestResponseTime(data, header, directory, filename):
        millisecond_values = (np.array(data)*1000).tolist()
        x_title = "Data Transfer"
        y_title = "Duration [ms]"
        Results.BoxPlot(millisecond_values, header,x_title,y_title,directory, filename)

    @staticmethod
    def BoxPlot(data,labels, x_title, y_title,directory,filename):
        fig, ax = plt.subplots()
        # Create an axes instance
        # ax = fig.add_axes([0,0,1,1])
        bp = ax.boxplot(data, showfliers=False)
        plt.xticks([x+1 for x in range(len(labels))],labels)
        plt.xlabel(x_title)
        plt.ylabel(y_title)
        if Configuration.Save:
            Results.SaveFigure(plt, directory, filename)
            Results.WriteLineGraphData(data, labels, directory, filename)
        else:
            plt.show()
        Results.ClearFigure()

    def AnalysisRequestResponseCount(self):
        requestResponseFiles = [x for x in self.Files if not x.startswith("resource") and x.endswith(".json")]
        for file in requestResponseFiles:
            try:
                filename = file.replace(".json", "")
                samples = FileOperations.ReadJsonFile(self.directory, file)
                requests = []
                responses = []
                timestamps = []

                for sample in samples:
                    requests.append(sample.get('request'))
                    responses.append(sample.get('response'))
                    timestamps.append(sample.get('time'))

                xpoints = np.array(timestamps)
                xpoints = xpoints - xpoints[0]
                directory = FileOperations.ProcessedResults + self.directory + "/" + filename + "/"
                Results.PlotLineGraph(xpoints, requests, "Time [s]", "Request Count [req/sec]", directory, "requests")
                Results.PlotLineGraph(xpoints, responses, "Time [s]", "Response Count [res/sec]", directory, "response")
            except Exception as err:
                print("Error Request Response: " + self.directory + "/" + file)
                print(err)
                print()



    def AnalysisResourceFiles(self):

        resource_files = [x for x in self.Files if x.startswith("resource") and x.endswith(".json")]


        for filename in resource_files:

            records = FileOperations.ReadJsonFile(self.directory, filename)
            filename = filename.replace(".json", "")
            csv_lines = ["timestamp;process_time;cpu_usage;memory_usage;total_memory\n"]
            processed_records = []
            start_time = None
            for record in records:
                processed_record = Results.ProcessResourceRecord(record, start_time)
                if start_time is None:
                    start_time = processed_record[0]
                csv_lines.append( ";".join([str(x) for x in processed_record]) + "\n")
                processed_records.append(processed_record)
            directory = FileOperations.ProcessedResults + self.directory+'/'
            FileOperations.WriteLines(directory, filename+".csv", csv_lines)
            Results.PlotCPUTimes(processed_records, directory, filename)
            Results.PlotMemoryUsage(processed_records, directory, filename)

    @staticmethod
    def ProcessResourceRecord(record, start_time):
        timestamp = record["timestamp"]
        process_time = timestamp - start_time if start_time is not None else 0
        cpu_usage = record["cpu_percentage"]["total"]["usage"]
        memory_usage = (record["totalmem"] - record["freemem"]) / record["totalmem"] * 100
        total_memory = record["totalmem"]


        return [timestamp, process_time, cpu_usage, memory_usage, total_memory]

    @staticmethod
    def PlotCPUTimes(processed_records, directory, filename):
        filename = "cpu_usage_"+filename
        x = [x[1] for x in processed_records]
        y = [x[2] for x in processed_records]
        x_title = "time [s]"
        y_title = "CPU Usage [%]"
        Results.PlotLineGraph(x, y, x_title, y_title, directory,filename)
        return y

    @staticmethod
    def PlotMemoryUsage(processed_records, directory, filename):
        filename = "memory_usage_"+filename
        x = [x[1] for x in processed_records]
        y = [x[3] for x in processed_records]
        x_title = "time [s]"
        y_title = "CPU Usage [%]"
        Results.PlotLineGraph(x, y, x_title, y_title, directory,filename)
        return y


    @staticmethod
    def PlotLineGraph(x, y, x_label, y_label, directory, filename):
        xpoints = np.array(x)
        ypoints = np.array(y)
        plt.plot(xpoints, ypoints, Configuration.Colors[0])
        plt.xlabel(x_label)
        plt.ylabel(y_label)

        if Configuration.Save:
            Results.SaveFigure(plt, directory, filename)
            Results.WriteLineGraphData([x, y], [x_label, y_label], directory, filename)
        else:
            plt.show()
        Results.ClearFigure()

    @staticmethod
    def WriteLineGraphData(value_arrays, headers, directory, filename):
        merged_list = list(zip(*value_arrays))
        df = pd.DataFrame(merged_list, columns=headers)
        df.to_csv(directory + filename + ".csv", sep=";")
        a = 1

    @staticmethod
    def ClearFigure():
        plt.figure().clear()
        plt.close()
        plt.cla()
        plt.clf()

    @staticmethod
    def SaveFigure(plt, directory, name):
        os.makedirs(directory, exist_ok=True)
        path = directory + name
        plt.savefig(path + '.jpeg', bbox_inches='tight')
        plt.savefig(path + '.pdf', bbox_inches='tight')
        plt.savefig(path + '.eps', bbox_inches='tight', transparent=True)
        plt.savefig(path + '.png', bbox_inches='tight')
        plt.savefig(path + '.svg', bbox_inches='tight', format="svg", transparent=True)
        plt.savefig(path + '.tiff', bbox_inches='tight')


def Main():
    FileOperations.CreateFolderIfNotExists(FileOperations.ProcessedResults)
    ResultsDirectories = FileOperations.GetResultsDirectoryNames()
    count = 1
    size = len(ResultsDirectories)
    for result in ResultsDirectories:
        print("["+str(count)+"/"+str(size)+"] Test name: "+result)
        Results(result)
        print("Finished")
        count+=1
    directory = FileOperations.ProcessedResults+"TotalResponseTime/"
    Results.TotalRequestResponseTime(RequestTime.TotalResponseTime, RequestTime.TotalResponseTimeHeaders,directory, "TotalResponse" )

if __name__ == '__main__':
    Main()
