var DeviceTypes = {
    User: 0,
    Cloud: 1,
    Broker: 2,
    Worker: 3,
    UserInterface: 4,
    ProcessMaster: 5,

    GetDeviceName: (deviceType) => {
        switch (deviceType) {
            case DeviceTypes.User:
                return 'User';
            case DeviceTypes.Cloud:
                return 'Cloud';
            case DeviceTypes.Broker:
                return 'Broker';
            case DeviceTypes.Worker:
                return 'Worker';
            case DeviceTypes.UserInterface:
                return 'User Interface';
            case DeviceTypes.ProcessMaster:
                return 'Process Master';
        }
    }
}



module.exports = {
    CloudIp: '164.92.168.129',
    Delimiter: ";",
    RM_SamplingPeriod: 1000,         //Resource Manager Sampling Period
    RM_BufferSize: 100,             // Resource Manager Buffer Size
    Port: 27592,
    WorkerCPULimit:0.7,
    WorkerMemoryLimit : 0.7,
    UserPackageDirectory: "./UserPackage/",
    DeviceType: DeviceTypes.Worker,
    DeviceTypes: DeviceTypes
};
