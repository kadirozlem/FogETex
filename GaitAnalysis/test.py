from statistics import mean

from gait_analysis import *
from timeit import default_timer as timer

class Test:
    def __init__(self, name):
        print("Test started for "+name+".")
    @staticmethod
    def ClearModel():
        start = timer()
        GaitAnalysis.ClearModelData()
        end = timer()
        diff = (end -start)*1000
        print("Model and test data cleared at %0.2f ms" % diff)

    def Initiate(self):
        start = timer()
        GaitAnalysis.Initiate()
        end = timer()
        diff = (end -start)
        print("Model Initialize completed at %0.4f s" % diff)

    def CreateModel(self):
        start = timer()
        self.GaitAnalysis = GaitAnalysis()
        end = timer()
        diff = (end -start)
        print("Model created at %0.4f s" % diff)

    def Calibrate(self, data):
        total_start = timer()
        durations=[]
        for sample in data.Capacitance:
            msg = "1;%d" % sample
            start = timer()
            self.GaitAnalysis.Predict(msg)
            diff = (timer() -start)*1000
            durations.append(diff)
        total = timer()-total_start
        Test.PrintResult("Calibrate", min(durations),max(durations), mean(durations),total, len(data.Capacitance))


    def Predict(self, data):
        total_start = timer()
        durations=[]
        results=[]
        for samples in data:
            for sample in samples.Capacitance:
                msg = "0;%d" % sample
                start = timer()
                results.append(int(self.GaitAnalysis.Predict(msg)))
                diff = (timer() -start)*1000
                durations.append(diff)
        total = timer()-total_start
        #print(results)
        #labels, counts = np.unique(results,return_counts=True)
        #print(counts)
        Test.PrintResult("Predict", min(durations),max(durations), mean(durations),total, len(durations))


    @staticmethod
    def PrintResult(name, min, max, average, total, data_count):
        print("%20s" % ("["+name+"]"), end='')
        print("   Max: %4.2f ms" % max, end='')
        print("   Min: %4.2f ms" % min, end='')
        print("   Avg: %4.2f ms" % average, end='')
        print("   Total: %6.2f s" % total, end='')
        print("   DataCount: %6d" % data_count)


def StartTest():
    dataset = GetDataset()
    Test.ClearModel()
    for user_no in dataset:
        user_dict = dataset[user_no]
        for step_length in user_dict:
            (calibration_samples, step_list) = user_dict[step_length]
            test = Test(user_no+"/"+step_length)
            test.Initiate()
            test.CreateModel()
            test.Calibrate(calibration_samples)
            test.Predict(step_list)


if __name__ == '__main__':
    StartTest()
