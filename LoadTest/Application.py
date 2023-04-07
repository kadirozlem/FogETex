import os
import sys

current = os.path.dirname(os.path.realpath(__file__))
parent_directory = os.path.dirname(current) + "\\GaitAnalysis"
sys.path.insert(1, parent_directory)

import gait_analysis


class GaitAnalysisData:
    def __init__(self, user_no, step_length, calibration_data, test_data):
        self.UserNo = user_no
        self.StepLength = step_length
        self.CalibrationData = calibration_data.Capacitance
        self.CalibrationLen=len(self.CalibrationData)
        self.TestData = []
        for data in test_data:
            self.TestData.extend(data.Capacitance)
        self.TestDataLen=len(self.TestData)

class GaitAnalysis:
    Data_Directory = "../GaitAnalysis/Data/"
    Data = []
    DataLength = 0
    Name = "GaitAnalysis"

    @staticmethod
    def ReadAllData():
        gait_analysis.Config.data_directory = GaitAnalysis.Data_Directory
        data = gait_analysis.GetDataset()
        for user_no in data:
            for step_length in data[user_no]:
                test_data = data[user_no][step_length]
                GaitAnalysis.Data.append(GaitAnalysisData(user_no, step_length, test_data[0], test_data[1]))

    @staticmethod
    def GetData(index):
        return GaitAnalysis.Data[int(index) % len(GaitAnalysis.Data)]


