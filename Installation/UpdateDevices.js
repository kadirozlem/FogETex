const Config = require("../Config");

const axios = require('axios')



const DeviceIP=[
    "192.168.2.103",
    "164.92.168.129"
]


function UpdateDevice(ip){
    axios.get(`http://${ip}:${Config.Port}/DeviceStatus`)

        .then(res => console.log(res.data))
        .catch(err => console.log(err))
}

function UpdateDevices(){
    UpdateDevice(DeviceIP[0]);
}
function CheckDevices(){

}


function main(){
    if(process.argv.length>2){
        switch (process.argv[2].trim().toLowerCase()){
            case 'update':
                UpdateDevices();
                break;
            case 'check':
                CheckDevices();
                break;
            default:
                console.log('main(): Command cannot matched!');
        }
    }else{
        console.log('main(): Command is missing!');
    }
}

main();