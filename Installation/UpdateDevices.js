const Config = require("../Config");

const axios = require('axios');


const DeviceIP = [
    "192.168.1.101",
    "164.92.168.129"
]


function UpdateDevice(ip) {
    axios.get(`http://${ip}:${Config.Port}/UpdateDevice`, {timeout: 3000})

        .then(res => {
            const data = res.data;
            data.IP = ip;
            data.Port = Config.Port;
            console.log(data);
        })
        .catch(err => {
            if(err.code =="ECONNRESET" ||err.code == "ECONNABORTED"){
                console.log(`Device Closed: ${ip}:${Config.Port}`);
            }else{
                console.log(err)}
            });
}

function UpdateDevices() {
    DeviceIP.forEach(x=>UpdateDevice(x));
}

function CheckDevices() {
    DeviceIP.forEach(ip => {
        axios.get(`http://${ip}:${Config.Port}/DeviceStatus`, {timeout: 3000})

            .then(res => {
                const data = res.data;
                data.IP = ip;
                data.Port = Config.Port;
                console.log(data);

            }).catch(err => {

            console.log(err);

        });
    });
}

function main() {
    if (process.argv.length > 2) {
        switch (process.argv[2].trim().toLowerCase()) {
            case 'update':
                UpdateDevices();
                break;
            case 'check':
                CheckDevices();
                break;
            default:
                console.log('main(): Command cannot matched!');
        }
    } else {
        console.log('main(): Command is missing!');
    }
}

main();