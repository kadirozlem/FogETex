var os = require("os");
var Config = require("./Config");
const microtime = require("microtime");
const {Manager} = require("socket.io-client");
const axios = require('axios');
const fs = require('fs');
const config = require("./LoadTest/FogETexResourceManager/Config");
const childprocess = require("child_process");


class ResourceInfo {
    constructor(previous) {
        this.timestamp = microtime.nowDouble();
        this.cpu_times = this.cpuInfo();
        this.cpu_percentage = this.cpuPercentage(previous)
        this.freemem = os.freemem();
        this.totalmem = os.totalmem();
        this.system_uptime = os.uptime();
        this.process_uptime = process.uptime();
        this.network_stat = this.networkStats();
        this.network_bandwidth = this.bandwidth(previous)
    }

    cpuInfo() {
        var cpu = os.cpus();
        var cpuList = [];
        cpu.forEach(function (item) {
            cpuList.push(item.times);
        });
        return cpuList;
    }

    cpuPercentage(previous) {
        var total_idle = 0;
        var total_time = 0;
        var diffence = {
            total: null,
            cores: []
        };
        if (previous && previous.length != this.cpu_times.length) {
            for (var cpu in this.cpu_times) {
                var user = this.cpu_times[cpu].user - previous.cpu_times[cpu].user;
                var nice = this.cpu_times[cpu].nice - previous.cpu_times[cpu].nice;
                var sys = this.cpu_times[cpu].sys - previous.cpu_times[cpu].sys;
                var irq = this.cpu_times[cpu].irq - previous.cpu_times[cpu].irq;
                var idle = this.cpu_times[cpu].idle - previous.cpu_times[cpu].idle;
                var total = user + nice + sys + irq + idle;
                diffence.cores.push({idle: idle, total: total, usage: (1 - idle / total) * 100});
                total_idle += idle;
                total_time += total;
            }

        } else {
            for (var cpu in this.cpu_times) {
                var user = this.cpu_times[cpu].user;
                var nice = this.cpu_times[cpu].nice;
                var sys = this.cpu_times[cpu].sys;
                var irq = this.cpu_times[cpu].irq;
                var idle = this.cpu_times[cpu].idle;
                var total = user + nice + sys + irq + idle;
                diffence.cores.push({idle: idle, total: total, usage: (1 - idle / total) * 100});
                total_idle += idle;
                total_time += total;

            }
        }
        diffence.total = {idle: total_idle, total: total_time, usage: (1 - total_idle / total_time) * 100};
        //console.log("Idle: "+diffence.total.idle+ " - Total" +diffence.total.total+" - Usage:" +diffence.total.usage)

        return diffence;
    }

    networkStats() {
        if (config.IsWindows) {
            let response = childprocess.execSync('netstat -e').toString().match(/\d+/g)
            return {
                RX: {
                    Bytes: parseInt(response[0]),
                    Package: parseInt(response[2]) + parseInt(response[4])
                },
                TX: {
                    Bytes: parseInt(response[1]),
                    Package: parseInt(response[3]) + parseInt(response[5])
                }
            }
        } else {
            let response = childprocess.execSync('cat /sys/class/net/eth0/statistics/rx_bytes '
                +'&& cat /sys/class/net/eth0/statistics/rx_packets '
                +'&& cat /sys/class/net/eth0/statistics/tx_bytes '
                +'&& cat /sys/class/net/eth0/statistics/tx_packets').toString().match(/\d+/g);
            return {
                RX: {
                    Bytes: parseInt(response[0]),
                    Package: parseInt(response[1])
                },
                TX: {
                    Bytes: parseInt(response[2]),
                    Package: parseInt(response[3])
                }
            }
        }
    }

    bandwidth(previous) {
        let bw = {RX: {Bytes: 0, Package: 0}, TX: {Bytes: 0, Package: 0}}
        if (previous) {
            bw.RX.Bytes = this.network_stat.RX.Bytes - previous.network_stat.RX.Bytes;
            bw.RX.Package = this.network_stat.RX.Package - previous.network_stat.RX.Package;
            bw.TX.Bytes = this.network_stat.TX.Bytes - previous.network_stat.TX.Bytes;
            bw.TX.Package = this.network_stat.TX.Package - previous.network_stat.TX.Package;
        }
        return bw;
    }
}

class Resources {
    constructor(FogETex) {
        this.FogETex = FogETex;
        this.resourcesInfos = [];
        this.previous = null;
        this.tick();
        var t = this;
        this.timer = setInterval(function () {
            t.tick()
        }, Config.RM_SamplingPeriod);
        if (Config.DeviceType == Config.DeviceTypes.Broker) {
            this.ConnectParent(Config.CloudIp);
        } else if (Config.DeviceType == Config.DeviceTypes.Worker) {
            this.FindBrokerIPAndConnect()
        }

        if (!fs.existsSync(Config.UserPackageDirectory)) {
            fs.mkdirSync(Config.UserPackageDirectory, {recursive: true});
        }

    }

    SendResourceInfo(info) {
        //Send it to the User Interface
        if (this.Socket) {
            this.Socket.emit("resource_info", info);
        }
        this.FogETex.Socket.ui_clients['Home'].forEach(element => element.emit("resource_info", info))
    }

    FindBrokerIPAndConnect() {
        const resourceObj = this;
        console.log('Trying to find Broker Ip.');
        axios.get(`http://${Config.CloudIp}:${Config.Port}/Cloud/GetBrokerIp`, {timeout: 3000})
            .then(res => {
                if (res.data.err) {
                    console.log("Broker IP couldn't find.")
                    console.log(res.data.err);
                    console.log()
                    setTimeout(() => {
                        resourceObj.FindBrokerIPAndConnect()
                    }, 1000);
                } else {
                    console.log("Broker IP has been found!")
                    console.log("Broker IP: " + res.data.LocalIP)
                    resourceObj.ConnectParent(res.data.LocalIP);
                }
            })
            .catch(err => {
                console.log("ResourceManager.FindBrokerIPAndConnect(): Connection error.")
                console.log(err);
                console.log();
                setTimeout(() => {
                    resourceObj.FindBrokerIPAndConnect()
                }, 1000);
            });
    }

    ConnectParent(ip) {
        const resourceObj = this;
        const manager = new Manager(`http://${ip}:${Config.Port}`, {
            autoConnect: true,
            query: {
                DeviceType: Config.DeviceType
            }
        });
        const socket = this.FogETex.ResourceSocket = this.Socket = manager.socket("/");

        socket.on("connect", () => {
            console.log("Resource Socket Connected!");
            socket.emit('device_info', resourceObj.FogETex.DeviceInfo);
            const fog_children = resourceObj.FogETex.Socket.fog_children;
            if (fog_children) {
                for (const key in fog_children) {
                    const child = fog_children[key];
                    socket.emit('worker_device_info', key, child.DeviceInfo, child.ResourceInfos)
                }
            }
        });

        socket.on("disconnect", (reason) => {
            console.log(reason);
        });

        socket.on("connect_error", (reason) => {
            console.log("Cannot connect");
        });

    }

    GetBulkData() {

        const cpu_data = this.resourcesInfos.map(x => x.cpu_percentage.total.usage)
        const cores = this.resourcesInfos[this.resourcesInfos.length - 1].cpu_percentage.cores.map(x => x.usage);
        const request = this.resourcesInfos.map(x => x.user_package_total.request);
        const response = this.resourcesInfos.map(x => x.user_package_total.response);
        const memory = this.resourcesInfos.map(x => x.memoryUsage);
        const bandwidth_tx = this.resourcesInfos.map(x=> x.network_bandwidth.TX.Bytes);
        const bandwidth_rx = this.resourcesInfos.map(x=> x.network_bandwidth.RX.Bytes);
        return {cpu: cpu_data, cores: cores, request: request, response: response, memory:memory,bandwidth_tx:bandwidth_tx, bandwidth_rx:bandwidth_rx }
    }

    tick() {
        var temp_req_res = this.FogETex.Socket.users_package
        this.FogETex.Socket.users_package = {}
        var resourceInfo = new ResourceInfo(this.previous);
        this.resourcesInfos.push(resourceInfo);
        if (this.resourcesInfos.length >= Config.RM_BufferSize) {
            //var tempList=this.resourcesInfos;
            //this.resourcesInfos=[];
            this.resourcesInfos.shift()
        }
        this.previous = resourceInfo;
        resourceInfo.user_package = temp_req_res
        resourceInfo.user_package_total = {request: 0, response: 0}
        for (const key in temp_req_res) {
            const req_res = temp_req_res[key];
            resourceInfo.user_package_total.request += req_res.request;
            resourceInfo.user_package_total.response += req_res.response;
            req_res.time = microtime.nowDouble();
            try {
                fs.appendFile(Config.UserPackageDirectory + this.FogETex.Socket.users[key].FileName, JSON.stringify(req_res) + "\n", (err) => {
                    if (err) console.log(err);
                })
            } catch (err) {
                console.log(err)
                let a = 1;
            }
        }

        if (Config.DeviceType == Config.DeviceTypes.Broker) {
            const children = this.FogETex.Socket.fog_children;
            resourceInfo.NodeBusy = true;
            for (const key in children) {
                const child = children[key]
                if (!child.Busy) {
                    resourceInfo.NodeBusy = false;
                    break;
                }
            }

        }

        this.SendResourceInfo(resourceInfo);
        //console.log(this.previous);

    }

}

module.exports = Resources;
