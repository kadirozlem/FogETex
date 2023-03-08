const Config = require("../Config");
const fetch = require('node-fetch');


const DeviceIP=[
    "192.168.2.103",
    "164.92.168.129"
]


async function UpdateDevice(ìp){
    const response =fetch(`http://${ip}:${Config.Port}/UpdateDevice`);
    const data = await response.json();
    a=1;
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