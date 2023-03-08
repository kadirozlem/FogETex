var os = require("os");
var Config=require("./Config");
const microtime = require("microtime");
const { Manager  } = require("socket.io-client");
const axios = require('axios')



class ResourceInfo {
    constructor(previous) {
        this.timestamp = microtime.nowDouble();
        this.cpu_times = this.cpuInfo();
        this.cpu_percentage = this.cpuPercentage(previous)
        this.freemem = os.freemem();
        this.totalmem = os.totalmem();
        this.system_uptime = os.uptime();
        this.process_uptime = process.uptime();
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
                diffence.cores.push({idle: idle, total: total, usage:(1-idle/total)*100});
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
                diffence.cores.push({idle: idle, total: total, usage:(1-idle/total)*100});
                total_idle += idle;
                total_time += total;

            }
        }
        diffence.total = {idle: total_idle, total: total_time, usage:(1-total_idle/total_time)*100};
        //console.log("Idle: "+diffence.total.idle+ " - Total" +diffence.total.total+" - Usage:" +diffence.total.usage)

        return diffence;
    }
}

class Resources {
    constructor(FogETex) {
        this.FogETex = FogETex;
        this.resourcesInfos=[];
        this.previous=null;
        this.tick();
        var t = this;
        this.timer=setInterval(function(){t.tick()},Config.RM_SamplingPeriod);
        if(Config.DeviceType != Config.DeviceTypes.Cloud){
            this.ConnectParent();
        }
    }

    SendResourceInfo(info){
        //Send it to the User Interface
        this.FogETex.Socket.ui_clients['Home'].forEach(element => element.emit("resource_info", info))
    }

    async ConnectParent(){
        //Axios add

        const manager = new Manager("ws://localhost:"+Config.Port, {
            autoConnect: true,
            query: {
                DeviceType: Config.DeviceTypes.Worker
            }
        });

        this.Socket = manager.socket("/");
    }

    GetBulkData(){

        const cpu_data= this.resourcesInfos.map(x=> x.cpu_percentage.total.usage)
        const cores=this.resourcesInfos[this.resourcesInfos.length-1].cpu_percentage.cores.map(x=>x.usage);
        const request = this.resourcesInfos.map(x=> x.user_package_total.request);
        const response = this.resourcesInfos.map(x=> x.user_package_total.response);
        return {cpu:cpu_data, cores: cores, request:request, response: response }
    }

    tick(){
        var temp_req_res=this.FogETex.Socket.users_package
        this.FogETex.Socket.users_package={}
        var resourceInfo=new ResourceInfo(this.previous);
        this.resourcesInfos.push(resourceInfo);
        if(this.resourcesInfos.length>=Config.RM_BufferSize){
            //var tempList=this.resourcesInfos;
            //this.resourcesInfos=[];
            this.resourcesInfos.shift()
        }
        this.previous=resourceInfo;
        resourceInfo.user_package=temp_req_res
        resourceInfo.user_package_total={request:0, response:0}
        for(const key in temp_req_res){
            resourceInfo.user_package_total.request+=temp_req_res[key].request;
            resourceInfo.user_package_total.response+=temp_req_res[key].response;
        }

        if(Config.DeviceType==Config.DeviceTypes.Broker){
            const children=this.FogETex.Socket.fog_children;
            resourceInfo.NodeBusy=true;
            for(const key in children){
                const child = children[key]
                if(child.ResourceInfos.length){
                    const last_resource = child.ResourceInfos[child.ResourceInfos.length - 1]
                    const cpu_usage = last_resource.cpu_percentage.total.usage;
                    const memory_usage = 100*(last.totalmem - info.freemem) / info.totalmem;
                    if(cpu_usage<Config.WorkerCPULimit && memory_usage< Config.WorkerMemoryLimit ){
                        resourceInfo.NodeBusy=false;
                        break;
                    }
                }
            }

        }

        this.SendResourceInfo(resourceInfo);
        //console.log(this.previous);

    }

}
module.exports=Resources;
