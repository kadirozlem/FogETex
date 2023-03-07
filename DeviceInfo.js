var geoip = require('geoip-lite');
const {execSync} = require("child_process");
const {Region, PublicIp} = require("./DeviceInfo");
const Config = require("./Config");
const os = require("os");
const nodeDiskInfo = require('node-disk-info');
const {getDiskInfoSync} = require("node-disk-info");
const lookup = require('country-code-lookup')
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
    });
    arr.sort((a,b)=>a-b);
    let cpu_Strings=[]
    arr.forEach(element=>{
        cpu_Strings.push(element.count + ' x '+ element.model)
    });

    return {array: arr, string: cpu_Strings.join("<br />")};
}

function GetDiskInfo() {
    const disks = nodeDiskInfo.getDiskInfoSync();
    const diskInfo = []
    const diskStrings=[]
    const power = os.platform()=='win32' ? 30 :20;
    disks.sort((a,b) => b.blocks - a.blocks);
    for (const disk of disks) {
        const obj ={
            FileSystem: disk.filesystem,
            Blocks: disk.blocks,
            Used: disk.used,
            Available: disk.available,
            Capacity: disk.capacity,
            Mounted: disk.mounted,
            String: disk.filesystem+ '('+disk.mounted+') - Capacity: '+(disk.blocks/Math.pow(2, power)).toFixed(2)+' GB'
        }
        diskInfo.push(obj);
        diskStrings.push(obj.String)
    }
    return {disks: diskInfo, diskString:diskStrings.join('<br />')};
}

var publicIP = getPublicIP();
var localIP = getLocalIP();
console.log(localIP)
var geo = geoip.lookup(publicIP);
var country_info = lookup.byInternet(geo.country);
module.exports = {
    DeviceType: Config.DeviceType,
    DeviceTypeString: DeviceTypes.GetDeviceName(Config.DeviceType),
    PublicIp: publicIP,
    LocalIp: localIP,
    Country: country_info.country,
    Continent: country_info.continent,
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
