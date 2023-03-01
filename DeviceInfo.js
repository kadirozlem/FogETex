var geoip = require('geoip-lite');
const {execSync} = require("child_process");
const {Region, PublicIp} = require("./DeviceInfo");
const Config = require("./Config");
const os = require("os");
const nodeDiskInfo = require('node-disk-info');
const {getDiskInfoSync} = require("node-disk-info");
const {DeviceTypes} = require("./Config");

function getPublicIP() {
    const cmd = `curl -s http://checkip.amazonaws.com || printf "0.0.0.0"`;
    const pubIp = execSync(cmd).toString().trim();
    return pubIp
}

function getLocalIP() {
    const {networkInterfaces} = require('os');

    const nets = networkInterfaces();

    for (const name of Object.keys(nets)) {
        for (const net of nets[name]) {
            const familyV4Value = typeof net.family === 'string' ? 'IPv4' : 4
            if (net.family === familyV4Value && !net.internal) {
                return net.address;
            }
        }
    }
}

function GetCPUInfo() {
    const cpus = os.cpus()
    const cpu_dict = {}
    const arr = []
    cpus.forEach((element) => {
        const key = element.model + element.speed
        if (cpu_dict[key]) {
            cpu_dict[key].count++;
        } else {
            let obj = cpu_dict[key] = {model: element.model, speed: element.speed, count: 1}
            arr.push(obj)
        }
    })
    return arr;
}

function GetDiskInfo() {
    const disks = nodeDiskInfo.getDiskInfoSync();
    const diskInfo = []
    for (const disk of disks) {
        diskInfo.push({
            FileSystem: disk.filesystem,
            Blocks: disk.blocks,
            Used: disk.used,
            Available: disk.available,
            Capacity: disk.capacity,
            Mounted: disk.mounted
        });
    }
    return diskInfo;
}

var publicIP = getPublicIP();
var localIP = getLocalIP();
console.log(localIP)
var geo = geoip.lookup(publicIP);

module.exports = {
    DeviceType: Config.DeviceType,
    DeviceTypeString: DeviceTypes.GetDeviceName(Config.DeviceType),
    PublicIp: publicIP,
    LocalIp: localIP,
    Country: geo.country,
    Region: geo.region,
    Timezone: geo.timezone,
    City: geo.city,
    Location: geo.ll,
    SystemInformation: {
        OperatingSystem: {
            Platform: os.platform(),
            Type: os.type(),
            Release: os.release()
        },
        CPUs: GetCPUInfo(),
        Memory: os.totalmem(),
        Disk: GetDiskInfo()
    },
    ConnectedDevices : []
}
