const { Manager  } = require("socket.io-client");
const Config = require("../Config");

class UserImitator{
    constructor(url,user_socket) {
        this.url = url+Config.Port;

    }

    connectToSocket(){
        const user_imitator=this;
        const manager = new Manager(this.url, {
            autoConnect: true,
            query: {
                DeviceType: Config.DeviceTypes.User
            }
        });
        this.socket = manager.socket("/");

        this.socket.on("process_ready", function (message){
            user_imitator.emit("process_ready", message)
        });

        this.socket.on("application_disconnected", function (message){
            user_imitator.emit("application_disconnected", message)
        });


    }
    close(){

    }

    sensorData(){

    }

    emit(){

    }

    appInfo(){

    }

}

module.exports=UserImitator;