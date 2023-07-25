var DeviceTypes = {
    User: 0,
    Cloud: 1,
    Broker: 2,
    Worker: 3,
    UserInterface: 4,
    ProcessMaster: 5,
    ExternalUser: 6,
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
            case DeviceTypes.ExternalUser:
                return 'External User'
        }
    }
}



module.exports = {
    CloudIp: '164.92.168.129',
    Delimiter: ";",
    RM_SamplingPeriod: 1000,         //Resource Manager Sampling Period
    RM_BufferSize: 100,             // Resource Manager Buffer Size
    Port: 27592,
    WorkerCPULimit:70,
    WorkerMemoryLimit : 70,
    UserPackageDirectory: "./UserPackage/",
    DeviceType: DeviceTypes.Broker,
    DeviceTypes: DeviceTypes
};
