const express = require("express");
const Config = require("../../Config");
const router = express.Router();
const shell = require('shelljs')

router.get('/', function (req, res, next){

    res.render('index',{title:"FogETex", UserType:Config.DeviceTypes.UserInterface, DeviceInfo:req.app.FogETex.DeviceInfo,Directory: 'Home'})
});

router.get('/DeviceStatus', (req, res, next)=>{
    res.json({Status: 'Running', DeviceType: req.app.FogETex.DeviceInfo.DeviceTypeString});
});

router.get('/UpdateDevice', (req, res,next)=>{
    res.redirect('/DeviceStatus');
    shell.exec('sh Update.sh')
});

module.exports = router;