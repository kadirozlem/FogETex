import torch
from torch import nn
from torch.autograd import Variable


class LSTM_Config:
    num_epochs = 100  # 50 epochs
    learning_rate = 0.001  # 0.001 lr

    input_size = 4  # number of features
    hidden_size = 4  # number of features in hidden state
    num_layers = 1  # number of stacked lstm layers

    num_classes = 4  # number of output classes
    neuron_count = 64


# Define the model
class LSTMModel(nn.Module):  # Inherit from nn.Module
    def __init__(self, seq_length, num_classes=LSTM_Config.num_classes, input_size=LSTM_Config.input_size,
                 hidden_size=LSTM_Config.hidden_size, num_layers=LSTM_Config.num_layers):
        super(LSTMModel, self).__init__()  # Initialize the super class
        self.num_classes = num_classes  # number of classes
        self.num_layers = num_layers  # number of layers
        self.input_size = input_size  # input size
        self.hidden_size = hidden_size  # hidden state
        self.seq_length = seq_length  # sequence length

        self.lstm_1 = nn.LSTM(input_size=input_size, hidden_size=hidden_size, num_layers=num_layers,
                              batch_first=True)  # lstm 1
        self.lstm_2 = nn.LSTM(input_size=hidden_size, hidden_size=hidden_size, num_layers=num_layers,
                              batch_first=True)  # lstm 2
        self.fc_1 = nn.Linear(hidden_size, LSTM_Config.neuron_count)  # fully connected 1
        self.fc = nn.Linear(LSTM_Config.neuron_count, num_classes)  # fully connected last layer

        self.relu = nn.ReLU()

    def forward(self, x):
        h_0 = Variable(torch.zeros(self.num_layers, x.size(0), self.hidden_size))  # hidden state
        c_0 = Variable(torch.zeros(self.num_layers, x.size(0), self.hidden_size))  # internal state
        # Propagate input through LSTM
        output, (hn, cn) = self.lstm_1(x, (h_0, c_0))  # lstm with input, hidden, and internal state
        output, (hn, cn) = self.lstm_2(self.relu(output), (hn, cn))  # lstm with input, hidden, and internal state
        hn = hn.view(-1, self.hidden_size)  # reshaping the data for Dense layer next
        out = self.relu(hn)  # relu activation
        out = self.fc_1(out)  # first Dense
        out = self.relu(out)  # relu activation
        out = self.fc(out)  # Final Output
        return out
