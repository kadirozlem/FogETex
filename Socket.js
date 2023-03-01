var microtime = require('microtime')
const Config = require("./Config");

let users = {};

function GetCandidateUserId() {
    let i = 1;
    while (users[i]) {
        i++
    }
    users[i] = true;
    return i;
}

module.exports=function (FogEtex) {
    var io = FogEtex.Socket;
    var users = {}
    var process_master = null;
    io.resource_members = []
    io.users_package = {}


    io.on("connection", (socket) => {
        socket.devicetype= parseInt(socket.handshake.query.DeviceType || Config.DeviceTypes.User);
        socket.deviceId = GetCandidateUserId();
        console.log(Config.DeviceTypes.GetDeviceName(socket.devicetype)+" connected");

        if(Config.DeviceType=Config.DeviceTypes.Broker){
            socket.on("resource_info",(resourceInformation)=>{

            });
        }


        socket.on("disconnect", (reason) => {
            console.log("User disconnected " + reason)
            if (socket == process_master) {
                process_master = null;
            }
            if (users[socket.id]) {
                if (users[socket.id].process) {
                    users[socket.id].process.emit("user_disconnected", socket.id)
                }
                delete users[socket.id]
            } else {
                for (var key in users) {
                    if (users[key].process == socket) {
                        users[key].user.emit("application_disconnected", true);
                        delete users[key]
                    }
                }
            }

            var resource_index = io.resource_members.indexOf(socket);
            if (resource_index !== -1) {
                io.resource_members.splice(resource_index, 1);
                console.log(socket.id + " element removed from resource_members")

            }

        });

        socket.on("sensor_data", (obj) => {
            obj.time_info["socket_received"] = microtime.nowDouble();
            users[socket.id].process.emit("sensor_data", socket.id, obj.data, obj.time_info);
            if (!io.users_package[socket.id]) {
                io.users_package[socket.id] = {index: socket.user_index, request: 1, response: 0}
            } else {
                io.users_package[socket.id].request++;
            }
        });

        socket.on("master_info", (status) => {
            if (status) {
                process_master = socket;
            }
        });

        socket.on("app_info", (obj) => {
            users[socket.id] = {index: obj.index, user: socket, process: null}
            socket.user_index = obj.index
            if (process_master) {
                process_master.emit("new_user", socket.id, obj.application);
            } else {
                socket.emit("process_ready", false, "Master is not ready");
            }
        });
        socket.on("process_ready", (obj) => {
            if (!users[obj.username]) {
                console.log('User not found: ' + obj.username)
                return
            }

            users[obj.username].user.emit("process_ready", obj.status, obj.info)
            if (!obj.status) {
                delete users[obj.username]
            } else {
                users[obj.username].process = socket
            }
        });

        socket.on("result", (obj) => {
            if (!users[obj.username]) {
                //console.log(obj.username+'User not found!')
                return
            }
            obj.time_info["result_received_socket"] = microtime.nowDouble();
            users[obj.username].user.emit("result", obj.result, obj.time_info);
            if (!io.users_package[obj.username]) {
                io.users_package[obj.username] = {index: socket.user_index, request: 0, response: 1}
            } else {
                io.users_package[obj.username].response++;
            }
        });

        socket.on("register_resource", (obj) => {
            io.resource_members.push(socket)
        });
    });

    io.SendResourceInfo = function (info) {
        io.resource_members.forEach(element => element.emit("resource_info", info));
    }
}
