var microtime = require('microtime')
const Config = require("./Config");
const Helper = require("./Helper");
const UserImitator = require("./UserImitator");
//const UserImitator = require('UserImitator');
let users = {};

module.exports=function (FogEtex) {
    const io = FogEtex.Socket;
    io.users = {}
    io.ui_clients = {'Home':[]}
    io.fog_children={}
    io.process_master = null;
    io.users_package = {}
    io.users_package_buffer={}

    io.GetCandidateUserId= function (){
        let i = 1;

        while (io.users[i.toString()]) {
            i++;
        }
        io.users[i.toString()] = true;
        return i.toString();
    }

    io.on("connection", (socket) => {
        socket.DeviceType= parseInt(socket.handshake.query.DeviceType || Config.DeviceTypes.User);
        console.log(Config.DeviceTypes.GetDeviceName(socket.DeviceType)+" connected");

        if(socket.DeviceType==Config.DeviceTypes.Broker){
            io.fog_children[socket.id] = { DeviceInfo: null, FogBusy: true, ResourceInfos:[], Children:{}}

            socket.on('device_info', (device_info)=>{
                io.fog_children[socket.id].DeviceInfo = device_info;
                io.SendAllUserInterface('device_info', {SocketId : socket.id, DeviceInfo:device_info} );
            });

            socket.on('resource_info', (resource_info)=>{
                io.fog_children[socket.id].NodeBusy = resource_info.NodeBusy;
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

            socket.on('worker_device_info', (socket_id,device_info, resource_info)=>{
                io.fog_children[socket.id].Children[socket_id]={DeviceInfo : device_info, ResourceInfos:resource_info}
                io.SendAllUserInterface('worker_device_info', {SocketId:socket_id, ParentId: socket.id, DeviceInfo:device_info} );
            });

            socket.on('worker_resource_info', (socket_id, resource_info)=>{
                if(!io.fog_children[socket.id].Children[socket_id]) {console.log("Worker cannot found in resource info"); return;}
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
                io.SendAllUserInterface('worker_disconnected',{SocketId:socket_id, ParentId: socket.id,Reason:reason});
                if(io.fog_children[socket.id]){
                    if(io.fog_children[socket.id].Children[socket_id]) {
                        delete io.fog_children[socket.id].Children[socket_id];
                    }
                }
            });

            socket.on('disconnect',(reason) =>{
                io.SendAllUserInterface('device_disconnected',{SocketId:socket.id, Reason:reason});
                const key = socket.id;
                if(io.fog_children[key]){
                    delete io.fog_children[key];
                }
            })


        }

        if(socket.DeviceType==Config.DeviceTypes.Worker){
            io.fog_children[socket.id] = { DeviceInfo: null, Busy:true, ResourceInfos:[]}

            socket.on('device_info', (device_info)=>{
                io.fog_children[socket.id].DeviceInfo = device_info;
                io.SendAllUserInterface('device_info', {SocketId : socket.id, DeviceInfo:device_info} );
                FogEtex.ResourceManager.Socket.emit('worker_device_info', socket.id, device_info, []);
            });

            socket.on('resource_info', (resource_info)=>{
                const cpu_usage = resource_info.cpu_percentage.total.usage;
                const memory_usage = 100*(resource_info.totalmem - resource_info.freemem) / resource_info.totalmem;
                io.fog_children[socket.id].Busy = cpu_usage>Config.WorkerCPULimit || memory_usage> Config.WorkerMemoryLimit;
                io.fog_children[socket.id].CPU_Usage = cpu_usage;
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
                io.SendAllUserInterface('device_disconnected',{SocketId:socket.id, Reason:reason});
                const key = socket.id;
                if(io.fog_children[key]){
                    delete io.fog_children[key];
                }
            });
        }

        if(socket.DeviceType == Config.DeviceTypes.ProcessMaster){
            io.process_master = socket;

            socket.on("disconnect", (reason) => {
                console.log("Process master disconnected " + reason);
                for(var key in io.users ){
                    io.users[key].emit("application_disconnected", true);
                }
                io.process_master = null;
            });

            //msg -> userid;status -> 12|1  or 12|1;AppNotCreate
            socket.on("process_ready", (msg) => {
                const [userId, status_msg] =msg.split("|");
                if (!io.users[userId]) {
                    console.log('User not found: ' + userId)
                    return
                }

                io.users[userId].emit("process_ready", status_msg)
            });
            //req: msg -> 'userId|socket_received|data_index;result;added_queue;process_started;process_finished'
            //response -> 'data_index;result;added_queue;process_started;process_finished;response_time'
            socket.on("result", (msg) => {
                const result_received_socket = microtime.nowDouble();
                const [userId, socket_received, result]=msg.split("|");
                if (!io.users[userId]) {
                    //console.log(obj.username+'User not found!')
                    return
                }

                const response_time = result_received_socket - parseFloat(socket_received);
                const response = result+";"+response_time;


                io.users[userId].emit("result", response);

                if (!io.users_package[userId]) {
                    io.users_package[userId] = {request: 0, response: 1}
                } else {
                    io.users_package[userId].response++;
                }
            });

        }

        if(socket.DeviceType==Config.DeviceTypes.User){
            //If client is User, get small id to decrease communication message
            socket.userId = io.GetCandidateUserId();

            socket.on("disconnect", (reason) => {
                console.log("User disconnected " + reason)

                if (io.users[socket.userId]) {
                    if (io.process_master) {
                        io.process_master.emit("user_disconnected", socket.id)
                    }
                    delete io.users[socket.userId]
                }
            });
            //msg -> dataIndex|data -> 1|123;1
            socket.on("sensor_data", (msg) => {
                const socket_received = microtime.nowDouble();
                const message = `${socket.userId}|${msg}|${socket_received}`;
                io.process_master.emit("sensor_data", message);
                if (!io.users_package[socket.userId]) {
                    io.users_package[socket.userId] = {request: 1, response: 0}
                } else {
                    io.users_package[socket.userId].request++;
                }
            });

            //user_index -> 1  #Created by user
            //response -> false|msg   or true
            socket.on("app_info", (user_index) => {
                io.users[socket.userId] = socket;
                socket.user_index = user_index;
                if (io.process_master) {
                    io.process_master.emit("new_user", socket.userId+"|"+socket.id);
                } else {
                    socket.emit("process_ready", "0;Master is not ready");
                }

                socket.FileName =  socket.user_index+'_'+Helper.DateTimeAsFilename()+'_'+socket.id+".json";
                socket.emit('filename', socket.FileName);
            });



        }

        if(socket.DeviceType==Config.DeviceTypes.ExternalUser){
            //If client is User, get small id to decrease communication message
            socket.userId = io.GetCandidateUserId();
            //If client is User, get small id to decrease communication message
            const userImitator = new UserImitator(socket.handshake.query.URL,socket,io);
            socket.on("disconnect", (reason) => {
                console.log("External User disconnected " + reason)
                userImitator.close();
                if (io.users[socket.userId]) {
                    delete io.users[socket.userId]
                }
            });
            //msg -> dataIndex|data -> 1|123;1
            socket.on("sensor_data", (msg) => {
                const socket_received = microtime.nowDouble();
                const message = `${socket_received}#${msg}`;
                userImitator.sensorData(message);
                if (!io.users_package[socket.userId]) {
                    io.users_package[socket.userId] = {request: 1, response: 0}
                } else {
                    io.users_package[socket.userId].request++;
                }
            });

            //user_index -> 1  #Created by user
            //response -> false|msg   or true
            socket.on("app_info", (user_index) => {
                userImitator.appInfo(user_index);
                socket.FileName =  socket.user_index+'_'+Helper.DateTimeAsFilename()+'_'+socket.id+".json";
                socket.emit('filename', socket.FileName);
            });



        }

        if(socket.DeviceType==Config.DeviceTypes.UserInterface){
            socket.Directory = socket.handshake.query.Directory;
            socket.join('ui');
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

    io.SendAllUserInterface=function (eventName, message){
        for(const directory in io.ui_clients){
            io.ui_clients[directory].forEach(element => element.emit(eventName,message))
        }
    }
}
