const { Manager  } = require("socket.io-client");
const Config = require("../Config");

const manager = new Manager("ws://localhost:"+Config.Port, {
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

socket.on("connect_error", () => {
    console.log("Cannot connect");
});