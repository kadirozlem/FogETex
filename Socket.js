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
        socket.DeviceType= parseInt(socket.handshake.query.DeviceType || Config.DeviceTypes.User);
        //If client is User, get small id to decrease communication message
        if(socket.DeviceType == Config.DeviceTypes.User){
            socket.userId = io.GetCandidateUserId();
            socket.FileName =  Helper.DateTimeAsFilename()+'_'+socket.id;
            socket.emit('filename', socket.FileName);
        }
        console.log(Config.DeviceTypes.GetDeviceName(socket.DeviceType)+" connected");

        if(socket.DeviceType==Config.DeviceTypes.Worker){
            io.fog_children[socket.id] = { DeviceInfo: null, ResourceInfos:[]}

            socket.on('device_info', (device_info)=>{
                io.fog_children[socket.id].DeviceInfo = device_info;
                io.to('iu').emit('device_info', {SocketId : socket.id, DeviceInfo:device_info} );
                FogEtex.ResourceManager.Socket.emit('worker_device_info', socket.id, device_info);
            });

            socket.on('resource_info', (resource_info)=>{
                const arr=io.fog_children[socket.id].ResourceInfos;
                arr.push(resource_info);
                if (arr.length > Config.RM_BufferSize){
                    arr.shift()
                }
                if(io.ui_clients[socket.id]){
                    io.ui_clients[socket.id].forEach(x => x.emit('resource_info', resource_info));
                }
                FogEtex.ResourceManager.Socket.emit('worker_resource_info', socket.id, resource_info);
            });

            socket.on('disconnect',(reason) =>{
                FogEtex.ResourceManager.Socket.emit('worker_disconnected', socket.id, reason);
                io.to('iu').emit('device_disconnected',{SocketId:socket.id, Reason:reason});
                const key = socket.id;
                if(io.fog_children[key]){
                    delete io.fog_children[key];
                }
            });
        }

        if(socket.DeviceType==Config.DeviceTypes.Broker){
            io.fog_children[socket.id] = { DeviceInfo: null, ResourceInfos:[], Children:{}}

            socket.on('device_info', (device_info)=>{
                io.fog_children[socket.id].DeviceInfo = device_info;
                io.to('iu').emit('device_info', {SocketId : socket.id, DeviceInfo:device_info} );
            });

            socket.on('resource_info', (resource_info)=>{
                const arr=io.fog_children[socket.id].ResourceInfos;
                arr.push(resource_info);
                if (arr.length > Config.RM_BufferSize){
                    arr.shift()
                }
                const ui_clients = io.ui_clients[socket.id];
                if(ui_clients) {
                    ui_clients.forEach(x => x.emit('resource_info', resource_info));
                }
            });

            socket.on('worker_device_info', (socket_id,device_info)=>{
                io.fog_children[socket.id].Children[socket_id]={DeviceInfo : device_info, ResourceInfos:[]}
                io.to('iu').emit('device_info', {SocketId:socket_id, ParentId: socket.id, DeviceInfo:device_info} );
            });

            socket.on('worker_resource_info', (socket_id, resource_info)=>{
                const arr=io.fog_children[socket.id].Children[socket_id].ResourceInfos;
                arr.push(resource_info);
                if (arr.length > Config.RM_BufferSize){
                    arr.shift()
                }
                const ui_clients = io.ui_clients[socket.id+'_'+socket_id];
                if(ui_clients) {
                    ui_clients.forEach(x => x.emit('resource_info', resource_info));
                }
            });

            socket.on('worker_disconnected', (socket_id, reason)=>{
                io.to('iu').emit('device_disconnected',{SocketId:socket_id, ParentId: socket.id,Reason:reason});
                const key = socket.id + _ + socket_id;
                if(io.fog_children[key]){
                    delete io.fog_children[key];
                }
            });

            socket.on('disconnect',(reason) =>{
                io.to('iu').emit('device_disconnected',{SocketId:socket.id, Reason:reason});
                const key = socket.id;
                if(io.fog_children[key]){
                    delete io.fog_children[key];
                }
            })


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
            socket.join('ui');
            if(!io.ui_clients[socket.Directory]){
                io.ui_clients[socket.Directory]=[]
            }
            io.ui_clients[socket.Directory].push(socket);

            if(socket.Directory=='Home'){
                socket.emit('bulk_data', FogEtex.ResourceManager.GetBulkData());
            }

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
