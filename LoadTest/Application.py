import os
import sys



current = os.path.dirname(os.path.realpath(__file__))
parent_directory = os.path.dirname(current)+"\\GaitAnalysis"
sys.path.insert(1,parent_directory)


import gait_analysis

class GaitAnalysis:
    Data_Directory="../GaitAnalysis/Data/"
    Data=[]
    DataLength=0
    Name="GaitAnalysis"

    @staticmethod
    def ReadAllData():
        gait_analysis.Config.data_directory = GaitAnalysis.Data_Directory
        GaitAnalysis.Data=gait_analysis.GetDataset()
