var microtime = require('microtime')
const Config = require("./Config");
const Helper = require("./Helper");

let users = {};

module.exports=function (FogEtex) {
    const io = FogEtex.Socket;
    io.users = {}
    io.ui_clients = {'Home':[]}
    io.fog_children={}
    io.process_master = null;
    io.resource_members = []
    io.users_package = {}
    io.users_package_buffer={}

    io.GetCandidateUserId= function (){
        let i = 1;
        while (io.users[i]) {
            i++
        }
        io.users[i] = true;
        return i;
    }

    io.on("connection", (socket) => {
        socket.devicetype= parseInt(socket.handshake.query.DeviceType || Config.DeviceTypes.User);
        //If client is User, get small id to decrease communication message
        if(socket.devicetype == Config.DeviceTypes.User){
            socket.userId = io.GetCandidateUserId();
            socket.FileName =  Helper.DateTimeAsFilename()+'_'+socket.id;
        }
        console.log(Config.DeviceTypes.GetDeviceName(socket.devicetype)+" connected");

        if(Config.DeviceType==Config.DeviceTypes.Broker){
            socket.on("resource_info",(resourceInformation)=>{

            });
        }

        if(socket.devicetype==Config.DeviceTypes.User){
            socket.on("disconnect", (reason) => {
                console.log("User disconnected " + reason)
                if (socket == process_master) {
                    process_master = null;
                }
                if (io.users[socket.id]) {
                    if (io.users[socket.id].process) {
                        io.users[socket.id].process.emit("user_disconnected", socket.id)
                    }
                    delete io.users[socket.id]
                } else {
                    for (var key in io.users) {
                        if (io.users[key].process == socket) {
                            io.users[key].user.emit("application_disconnected", true);
                            delete io.users[key]
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
                io.users[socket.id].process.emit("sensor_data", socket.id, obj.data, obj.time_info);
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
                io.users[socket.id] = {index: obj.index, user: socket, process: null}
                socket.user_index = obj.index
                if (process_master) {
                    process_master.emit("new_user", socket.id, obj.application);
                } else {
                    socket.emit("process_ready", false, "Master is not ready");
                }
            });
            socket.on("process_ready", (obj) => {
                if (!io.users[obj.username]) {
                    console.log('User not found: ' + obj.username)
                    return
                }

                io.users[obj.username].user.emit("process_ready", obj.status, obj.info)
                if (!obj.status) {
                    delete io.users[obj.username]
                } else {
                    io.users[obj.username].process = socket
                }
            });

            socket.on("result", (obj) => {
                if (!io.users[obj.username]) {
                    //console.log(obj.username+'User not found!')
                    return
                }
                obj.time_info["result_received_socket"] = microtime.nowDouble();
                io.users[obj.username].user.emit("result", obj.result, obj.time_info);
                if (!io.users_package[obj.username]) {
                    io.users_package[obj.username] = {index: socket.user_index, request: 0, response: 1}
                } else {
                    io.users_package[obj.username].response++;
                }
            });

            socket.on("register_resource", (obj) => {
                io.resource_members.push(socket)
            });
        }

        if(socket.devicetype==Config.DeviceTypes.UserInterface){
            socket.Directory = socket.handshake.query.Directory;

            if(!io.ui_clients[socket.Directory]){
                io.ui_clients[socket.Directory]=[]
            }
            io.ui_clients[socket.Directory].push(socket);

            socket.on("disconnect", (reason) => {
                var ui_index = io.ui_clients[socket.Directory].indexOf(socket);
                if (ui_index !== -1) {
                    io.ui_clients[socket.Directory].splice(ui_index, 1);
                    console.log(socket.Directory + " element removed from ui clients.")
                    //Delete array if all clients is disconnected.
                    if(socket.Directory!='Home' && io.ui_clients[socket.Directory].length==0){
                        delete io.ui_clients[socket.Directory];
                    }
                }
                console.log("User Interface disconnected " + reason);
            });
        }
    });

    io.SendResourceInfo = function (info) {
        io.resource_members.forEach(element => element.emit("resource_info", info));
    }
}
