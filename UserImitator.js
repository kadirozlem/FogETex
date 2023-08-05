const { Manager  } = require("socket.io-client");
const Config = require("./Config");
const microtime = require("microtime");

class UserImitator{
    constructor(url,user_socket, io) {

        this.url = url+":"+Config.Port;
        this.user_socket = user_socket;
        this.io = io;
        this.connectToSocket()
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
        this.socket.on("connect", function (){
            console.log("user imitator connected")
        });
        this.socket.on("connect_error",function (err){
            console.log("Worker: "+user_imitator.url + " disconnected!")
        });
        this.socket.on("disconnected",function (err){
            console.log("Worker: "+user_imitator.url + " disconnected!")
        });

        this.socket.on("process_ready", function (message){

            user_imitator.emit("process_ready", message)
        });

        this.socket.on("application_disconnected", function (message){
            user_imitator.emit("application_disconnected", message)
        });

        this.socket.on("result", function (msg){
            const result_received_socket = microtime.nowDouble();
            const [socket_received, result] =msg.split("#")

            const response_time = result_received_socket - parseFloat(socket_received);
            const response = result+";"+response_time;

            user_imitator.emit("result", response);

            if (!user_imitator.io.users_package[user_imitator.user_socket.userId]) {
                user_imitator.io.users_package[user_imitator.user_socket.userId] = {request: 0, response: 1}
            } else {
                user_imitator.io.users_package[user_imitator.user_socket.userId].response++;
            }
        });


    }
    close(){
        this.socket.close()
    }

    sensorData(msg){
        this.socket.emit("sensor_data",msg)
    }

    emit(eventName, msg){
        this.user_socket.emit(eventName,msg)
    }

    appInfo(msg){
        this.socket.emit("app_info",msg);
    }

}

module.exports=UserImitator;