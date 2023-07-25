import os
import shutil

from scipy import signal
import numpy as np
import matplotlib.pyplot as plt
from scipy.fftpack import fft, fftfreq
import statistics
import pandas as pd
from sklearn.metrics import f1_score, ConfusionMatrixDisplay
from model import LSTMModel, LSTM_Config
import torch
from torch.autograd import Variable
from pathlib import Path

class Config:
    Header = 1
    Frequency = 50
    Sample_Distance = 3
    SN_Cal_Start = 50
    SN_MinArrSize = 50
    File_Start_Sample = 100
    File_End_Sample = 450
    Test_Train_Ratio = 0.8
    Test_Results_Directory=r"./TestResults/"
    windowSize = 10
    slideCount = 5
    data_directory = r"./Data/"
    ModelPath = r"./Model/capacitance_model.pt"
    Print = False

def print_s(msg):
    if Config.Print:
        print(msg)


class ButterWorth:
    def __init__(self):
        self.b, self.a = signal.butter(3, 0.05)
        self.X = [0] * len(self.b)
        self.Y = [0] * (len(self.a) - 1)

    def SlideX(self, val):
        self.X.insert(0, val)
        self.X.pop()

    def SlideY(self, val):
        self.Y.insert(0, val)
        self.Y.pop()

    def Calculate(self, val):
        self.SlideX(val)
        sumX = sum([self.X[i] * self.b[i] for i in range(len(self.b))])
        sumY = sum([self.Y[i] * self.a[i + 1] for i in range(len(self.a) - 1)])
        filtered_Y = (sumX - sumY) / self.a[0]
        self.SlideY(filtered_Y)

        return filtered_Y


class StandartNormalizer:
    def __init__(self):
        self.counter = 0
        self.Mean = None
        self.StandardDeviation = None
        self.CalibrationArray = []

    def AddCalibrationValue(self, value):
        self.counter += 1
        if self.counter > Config.SN_Cal_Start:
            self.CalibrationArray.append(value)
        return -1

    def CalculateParameters(self):
        if len(self.CalibrationArray) < Config.SN_MinArrSize:
            raise Exception("Calibration error size is not enough!")

        self.Mean = statistics.mean(self.CalibrationArray)
        self.StandardDeviation = statistics.stdev(self.CalibrationArray)
        self.CalibrationArray = None

    def GetValue(self, value):
        if self.Mean is None:
            self.CalculateParameters()

        return (float(value) - self.Mean) / self.StandardDeviation


class FeatureExtraction:
    def __init__(self, distance=Config.Sample_Distance):
        self.distance = distance
        self.filter = ButterWorth()
        self.Capacitance = [0] * (self.distance + 1)
        self.Velocity = [0] * (self.distance + 1)
        self.Acceleration = [0] * (self.distance + 1)
        self.Jerk = None
        self.Calibration_Sample_Count = 0

        self.Normalizers = [StandartNormalizer(), StandartNormalizer(), StandartNormalizer(), StandartNormalizer()]

    def Get(self, raw_capacitance):
        capacitance = self.filter.Calculate(raw_capacitance)
        self.Capacitance.insert(0, capacitance)
        self.Capacitance.pop()

        velocity = (self.Capacitance[0] - self.Capacitance[self.distance]) / self.distance * Config.Frequency
        self.Velocity.insert(0, velocity)
        self.Velocity.pop()

        acceleration = (self.Velocity[0] - self.Velocity[self.distance]) / self.distance * Config.Frequency
        self.Acceleration.insert(0, acceleration)
        self.Acceleration.pop()

        jerk = (self.Acceleration[0] - self.Acceleration[self.distance]) / self.distance * Config.Frequency
        self.Jerk = jerk

        return [capacitance, velocity, acceleration, jerk]

    # User side arrange the calibration values.
    def GetNormalizedValue(self, raw_capacitance, cal=False):
        features = self.Get(raw_capacitance)
        normalized_values = []
        for i in range(len(features)):
            if cal:
                self.Calibration_Sample_Count += 1
                if self.Calibration_Sample_Count > Config.SN_Cal_Start:
                    normalized_values.append(self.Normalizers[i].AddCalibrationValue(features[i]))
            else:
                normalized_values.append(self.Normalizers[i].GetValue(features[i]))
        return normalized_values


def GaitPhasesFromIMU(timestamps, gyroz_data):
    gyroz_data = np.asarray(gyroz_data)  # convert to numpy array
    gyroz_df = pd.DataFrame(gyroz_data)
    timestamps = np.asarray(timestamps)  # convert to numpy array

    b, a = signal.butter(2, 2.5, fs=50, output='ba')  # butterworth filter
    gyroz_data_filt = signal.filtfilt(b, a, gyroz_data)  # apply filter

    try:
        # Use scipy peak detection for detecting toe-off mid-swing heel-strike events
        peaks = signal.argrelextrema(np.asarray(gyroz_data_filt), np.greater_equal, order=40)[0]
        peaks = [peak for peak in peaks if gyroz_data_filt[peak] > 10]
        peak_list = [gyroz_data_filt[i] if i in peaks else np.nan for i in range(len(timestamps))]

        troughs = signal.argrelextrema(np.asarray(gyroz_data_filt), np.less_equal, order=15)[0]
        troughs = [trough for trough in troughs if abs(gyroz_data_filt[trough]) > 10]
        trough_list = [gyroz_data_filt[i] if i in troughs else np.nan for i in range(len(timestamps))]

        heel_strike_list = trough_list.copy()
        toe_off_list = trough_list.copy()

        # Get phase change points using peaks and troughs
        lines = []
        toe_off = True
        for j in range(len(timestamps)):
            if j in peaks:
                toe_off = False
                lines.append((timestamps[j], 'Mid-swing', j))
            if toe_off and j in troughs:
                heel_strike_list[j] = np.nan
                lines.append((timestamps[j], 'Toe-off', j))
            if not toe_off and j in troughs:
                toe_off_list[j] = np.nan
                toe_off = True
                lines.append((timestamps[j], 'Heel-strike', j))

        # Calculate heel off from max of gyro-z values between heel strikes and toe-offs
        heel_offs = []
        new_lines = lines.copy()
        offset = 0

        for idx in range(len(lines) - 1):
            if lines[idx][1] == 'Heel-strike' and lines[idx + 1][1] == 'Toe-off':
                heel_strike_idx = lines[idx][2]
                toe_off_idx = lines[idx + 1][2]

                interval = gyroz_df[heel_strike_idx:toe_off_idx]
                interval = interval[len(interval) // 4:]
                interval = interval[interval < 0]
                heel_off_idx = interval.idxmax()
                heel_off_time = timestamps[heel_off_idx]
                new_lines.insert(idx + 1 + offset, (heel_off_time, 'Heel-off', heel_off_idx))
                offset += 1
                heel_offs.append(heel_off_idx[0])
        heel_off_list = [gyroz_data_filt[i] if i in heel_offs else np.nan for i in range(len(timestamps))]


    except KeyError as ke:
        print_s(ke)
        pass

    heel_strike_list = trough_list.copy()
    toe_off_list = trough_list.copy()

    toe_off = True
    for j in range(len(timestamps)):
        if j in peaks:
            toe_off = False
        if toe_off and j in troughs:
            heel_strike_list[j] = np.nan
        if not toe_off and j in troughs:
            toe_off_list[j] = np.nan
            toe_off = True

    mid_swing_list_bool = [not np.isnan(peak_list[j]) for j in range(len(timestamps))]
    heel_strike_list_bool = [not np.isnan(heel_strike_list[j]) for j in range(len(timestamps))]
    toe_off_list_bool = [not np.isnan(toe_off_list[j]) for j in range(len(timestamps))]
    heel_off_list_bool = [not np.isnan(heel_off_list[j]) for j in range(len(timestamps))]

    # Obtain gait phase from heel strike, toe off, mid swing and heel off points
    gait_phases = []
    gait_phase = 0
    for j, timestamp in enumerate(timestamps):
        if toe_off_list_bool[j]:
            gait_phase = 0
        if mid_swing_list_bool[j]:
            gait_phase = 1
        if heel_strike_list_bool[j]:
            gait_phase = 2
        if heel_off_list_bool[j]:
            gait_phase = 3
        gait_phases.append(gait_phase)
    return gait_phases

class SensorValues:
    def __init__(self):
        self.Time = []
        self.AccX = []
        self.AccY = []
        self.AccZ = []
        self.GyroX = []
        self.GyroY = []
        self.GyroZ = []
        self.Capacitance = []
        self.Labels = []

    def appendSample(self, sample_tex):
        if len(sample_tex) > 0:
            data = sample_tex.split(",")
            if len(data) == 8:
                self.Time.append(int(data[0]))
                self.AccX.append(float(data[1]))
                self.AccY.append(float(data[2]))
                self.AccZ.append(float(data[3]))
                self.GyroX.append(float(data[4]))
                self.GyroY.append(float(data[5]))
                self.GyroZ.append(float(data[6]))
                self.Capacitance.append(int(data[7]))
            else:
                a = 1

    def CalculateLabels(self):
        self.Labels = GaitPhasesFromIMU(self.Time, self.GyroZ)


def ReadFile(directory, start=0, end=None):
    sensor_values = SensorValues()
    with open(directory) as file:
        lines = file.readlines()
        start = start + Config.Header
        end = min(end, len(lines)) if end is not None else len(lines)
        for i in range(start, end):
            sensor_values.appendSample(lines[i].strip())
    sensor_values.CalculateLabels()
    return sensor_values


def GetFolders(path):
    return [name for name in os.listdir(path) if os.path.isdir(path + name)]


def ListCSVFiles(path):
    return [name for name in os.listdir(path) if name.lower().endswith(".csv")]


def GetDataset():
    data = {}
    print_s("Files are started reading.")
    for user_no in GetFolders(Config.data_directory):
        user_path = Config.data_directory + user_no + "/"
        data[user_no] = user_dict = {}
        for step_length in GetFolders(user_path):
            step_length_path = user_path + step_length + "/"
            step_list = []
            calibration_samples = None

            for sample_no in ListCSVFiles(step_length_path):
                sample_path = step_length_path + "/" + sample_no
                if calibration_samples is None:
                    calibration_samples = ReadFile(sample_path, end=Config.File_End_Sample)
                sensor_values = ReadFile(sample_path, end=Config.File_End_Sample)
                step_list.append(sensor_values)
            user_dict[step_length] = (calibration_samples, step_list)

    print_s(str(len(data)) + " user files readed.")
    return data

    # data 1 - calibration
    # data 1-8 train
    # data 9-10 test


class GaitAnalysis:
    Ready=False

    def __init__(self):
        self.FeatureExtraction=FeatureExtraction()
        self.Model= GaitAnalysis.LoadModels()

    @staticmethod
    def LoadModels():
        #Sequence length is 1, One sample will be predict for each step
        model = LSTMModel(1) # create model
        model.load_state_dict(torch.load(Config.ModelPath)) # load model
        model.eval() # set model to evaluation mode
        return model

    def Predict(self, data):
        data_splitted = data.split(";")
        cal = int(data_splitted[0])
        raw_cap = int(data_splitted[1])
        postfix= ";"+data_splitted[2] if len(data_splitted)>2 else ""
        features=self.FeatureExtraction.GetNormalizedValue(raw_cap,cal)
        if cal:
            return "-1"+postfix
        else:
            test_predict = self.Model(torch.Tensor([[features]]))  # forward pass
            _, predicted = torch.max(test_predict, 1)  # get the index of the max log-probability
            data_predict = predicted.data.numpy()
            return str(data_predict)+postfix

    @staticmethod
    def Initiate():
        os.makedirs(os.path.dirname(Config.ModelPath), exist_ok=True)
        os.makedirs(Config.Test_Results_Directory, exist_ok=True)
        if not os.path.exists(Config.ModelPath):
            GaitAnalysis.Train()
    @staticmethod
    def ClearModelData():
        if os.path.isdir(os.path.dirname(Config.ModelPath)):
            shutil.rmtree(os.path.dirname(Config.ModelPath))
        if os.path.isdir(Config.Test_Results_Directory):
            shutil.rmtree(Config.Test_Results_Directory)

    @staticmethod
    def Train():
        dataset = GetDataset()
        print_s("Files Started to process.")
        micro_f1s = []
        macro_f1s = []
        xs_train, ys_train, xs_test, ys_test = [], [], [], []
        for user_no in dataset:
            user_dict = dataset[user_no]
            for step_length in user_dict:
                (calibration_samples, step_list) = user_dict[step_length]
                feature_extraction = FeatureExtraction()
                for capacitance in calibration_samples.Capacitance:
                    feature_extraction.GetNormalizedValue(capacitance, cal=True)
                train_length = int(len(step_list) * Config.Test_Train_Ratio)
                train_set = step_list[:train_length]
                test_set = step_list[train_length:]
                # Prepare Normalized Train Data
                for step in train_set:
                    capacitance_list = step.Capacitance[Config.File_Start_Sample:]
                    label_list = step.Labels[Config.File_Start_Sample:]
                    normalized_data = []
                    for capacitance in capacitance_list:
                        normalized_data.append(feature_extraction.GetNormalizedValue(capacitance))
                    xs_train.append(np.asarray(normalized_data))
                    ys_train.append(np.asarray(label_list))

                # Prepare Normalized Test Data
                for step in test_set:
                    capacitance_list = step.Capacitance[Config.File_Start_Sample:]
                    label_list = step.Labels[Config.File_Start_Sample:]
                    normalized_data = []
                    for capacitance in capacitance_list:
                        normalized_data.append(feature_extraction.GetNormalizedValue(capacitance))
                    xs_test.append(np.asarray(normalized_data))
                    ys_test.append(np.asarray(label_list))

        xs_train = np.asarray(xs_train)
        ys_train = np.asarray(ys_train)
        xs_test = np.asarray(xs_test)
        ys_test = np.asarray(ys_test)

        xs_train_tensors, xs_test_tensors, ys_train_tensors, ys_test_tensors = [], [], [], []
        # convert train data to tensors
        for i in range(xs_train.shape[0]):
            X_train_tensors = Variable(torch.Tensor(xs_train[i]))
            y_train_tensors = Variable(torch.LongTensor(ys_train[i]))
            X_train_tensors_final = torch.reshape(X_train_tensors,
                                                  (X_train_tensors.shape[0], 1, X_train_tensors.shape[1]))
            xs_train_tensors.append(X_train_tensors_final)
            ys_train_tensors.append(y_train_tensors)

        # convert test data to tensors
        for i in range(xs_test.shape[0]):
            X_test_tensors = Variable(torch.Tensor(xs_test[i]))
            y_test_tensors = Variable(torch.LongTensor(ys_test[i]))
            X_test_tensors_final = torch.reshape(X_test_tensors, (X_test_tensors.shape[0], 1, X_test_tensors.shape[1]))
            xs_test_tensors.append(X_test_tensors_final)
            ys_test_tensors.append(y_test_tensors)

        xs_train_tensors = torch.stack(xs_train_tensors)  # stack all train tensors
        xs_test_tensors = torch.stack(xs_test_tensors)  # stack all test tensors
        ys_train_tensors = torch.stack(ys_train_tensors)  # stack all train tensors
        ys_test_tensors = torch.stack(ys_test_tensors)  # stack all test tensors

        model = LSTMModel(xs_train_tensors.shape[2])  # create model

        criterion = torch.nn.CrossEntropyLoss()  # mean squared error loss for regression
        optimizer = torch.optim.Adam(model.parameters(), lr=LSTM_Config.learning_rate)  # Adam optimizer

        losses = []
        epochs_trained = 0
        # train the model
        for epoch in range(LSTM_Config.num_epochs):
            running_loss = 0.0
            for i in range(xs_train_tensors.shape[0]):
                outputs = model(xs_train_tensors[i])  # forward pass
                optimizer.zero_grad()  # zero the gradient buffers
                loss = criterion(outputs, ys_train_tensors[i].flatten())  # compute loss
                loss.backward()  # backpropagation
                running_loss += loss.item()  # update running loss
                optimizer.step()  # update weights

            if epoch % (LSTM_Config.num_epochs // 10) == 0:
                print_s(f"Epoch: {epoch}, loss: {running_loss / xs_train_tensors.shape[0]:.2f}")  # print loss

            GaitAnalysis.test_loop(model,xs_test_tensors, ys_test_tensors, epoch, micro_f1s, macro_f1s)
            losses.append(running_loss / xs_train_tensors.shape[0])
            epochs_trained += 1
        torch.save(model.state_dict(), Config.ModelPath)  # save model
        GaitAnalysis.PlotF1Scores(micro_f1s, macro_f1s, epochs_trained, losses)

    @staticmethod
    def test_loop(model,xs_test_tensors,ys_test_tensors,  epoch,micro_f1s,macro_f1s):
        model.eval()  # set model to evaluation mode
        micro_f1 = 0.0
        macro_f1 = 0.0
        data_true = []
        data_prediction = []
        with torch.no_grad():  # do not calculate gradients
            for j in range(xs_test_tensors.shape[0]):
                test_predict = model(xs_test_tensors[j])  # forward pass
                dataY = ys_test_tensors[j].data.numpy()
                _, predicted = torch.max(test_predict, 1)  # get the index of the max log-probability
                data_predict = predicted.data.numpy()
                micro_f1 += f1_score(dataY, np.rint(data_predict), average='micro')  # calculate f1 score
                macro_f1 += f1_score(dataY, np.rint(data_predict), average='macro')  # calculate f1 score
                data_true.append(dataY.flatten().tolist())
                data_prediction.append(np.rint(data_predict).flatten().tolist())

        data_true = [int(data_true[j][k]) for j in range(len(data_true)) for k in range(len(data_true[0]))]
        data_prediction = [int(data_prediction[j][k]) for j in range(len(data_prediction)) for k in
                           range(len(data_prediction[0]))]
        if (epoch + 1) % (
                LSTM_Config.num_epochs // 5) == 0 or epoch == LSTM_Config.num_epochs - 1:  # display confusion matrix 5 times during training
            ConfusionMatrixDisplay.from_predictions(data_true,
                                                    data_prediction,
                                                    labels=[0, 1, 2, 3],
                                                    normalize='true',
                                                    display_labels=["Toe-off", "Mid-swing", "Heel-strike", "Heel-off"],
                                                    cmap=plt.cm.Blues,
                                                    xticks_rotation='vertical'
                                                    )
            plt.savefig(Config.Test_Results_Directory+f"cm_norm_{epoch + 1}.png", bbox_inches='tight', pad_inches=1)
            plt.clf()

        micro_f1s.append(micro_f1 / xs_test_tensors.shape[0])  # append f1 score to list
        macro_f1s.append(macro_f1 / xs_test_tensors.shape[0])  # append f1 score to list
        model.train()

    @staticmethod
    def PlotF1Scores(micro_f1s, macro_f1s, epochs_trained, losses):
        # Plot F1 score
        plt.clf()
        plt.plot(list(range(epochs_trained)), micro_f1s, label='Micro F1')
        plt.plot(list(range(epochs_trained)), macro_f1s, label='Macro F1')
        plt.legend(loc='lower right')
        plt.ylabel('F1 Score')
        plt.xlabel('Epoch')
        plt.title('F1 Score Plot')
        plt.savefig(Config.Test_Results_Directory+'F1_score_plot.png')
        plt.clf()
        # Plot Loss
        plt.plot(list(range(epochs_trained)), losses, label='Train Loss')
        plt.legend(loc='upper right')
        plt.ylabel('Train Loss')
        plt.xlabel('Epoch')
        plt.title('Loss Plot')
        plt.savefig(Config.Test_Results_Directory+'Loss_plot.png')
        print_s(f'{micro_f1s[-1]:.2f}')
        print_s(f'{max(micro_f1s):.2f}')

    def LoadModel(self):
        pass
