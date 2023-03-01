const express = require('express');
const http = require('http');
const { Server } = require("socket.io");
const Config = require("./Config");
const  Home_Route = require('./UserInterface/Routes/Home')
const  DeviceInfo = require('./DeviceInfo')
const app = require('./UserInterface')
const ResourceManager= require('./ResourceManager')




const server = http.createServer(app);
const io = new Server(server);
//Create a object to access application variables to share info and methods.
let FogETex = {Express:app, HttpServer:server, Socket:io, DeviceInfo:DeviceInfo, ResourceInformation:{}}
app.FogETex = FogETex;

const Socket = require('./Socket')(FogETex);
FogETex.ResourceManager = new ResourceManager(FogETex);
// io.on('connection', (socket) => {
//     console.log('a user connected');
// });

server.listen(Config.Port, () => {
    console.log('listening on *:'+Config.Port);
});