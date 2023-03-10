const { Manager  } = require("socket.io-client");
const Config = require("../Config");
const url = "ws://192.168.1.20:"+Config.Port;
const manager = new Manager(url, {
    autoConnect: true,
    query: {
        DeviceType: Config.DeviceTypes.Worker
    }
});

const socket = manager.socket("/");

socket.on("connect",()=>{
   console.log("Connected")
});

socket.on("resource_info",(info)=>{
    console.log(info);
})

socket.on("disconnect", (reason) => {
    console.log(reason);
});

socket.on("connect_error", (err) => {
    console.log("Cannot connect");
    console.log(err);
});
