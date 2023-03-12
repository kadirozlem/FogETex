const express = require("express");
const Config = require("../../Config");
const router = express.Router();
const shell = require('shelljs')
var pjson = require('../../package.json');

router.get('/', function (req, res, next) {
    const FogETex= req.app.FogETex;
    const FogChildren = {}
    for(const key in FogETex.Socket.fog_children){
        const child = FogETex.Socket.fog_children[key];
        FogChildren[key] = {DeviceInfo: child.DeviceInfo};

        if(child.Children){
            FogChildren[key].Children={};
            for(const key2 in child.Children){
                FogChildren[key].Children[key2]= {DeviceInfo:child.Children[key2].DeviceInfo}
            }
        }
    }

    res.render('index', {
        title: "FogETex",
        UserType: Config.DeviceTypes.UserInterface,
        DeviceInfo: FogETex.DeviceInfo,
        FogChildren: FogChildren,
        Directory: 'Home'
    })
});

router.get('/DeviceStatus', (req, res, next) => {
    res.json({Status: 'Running', DeviceType: req.app.FogETex.DeviceInfo.DeviceTypeString, Version: pjson.version});
});

router.get('/UpdateDevice', (req, res, next) => {
    res.redirect('/DeviceStatus');
    shell.exec('sh Update.sh')
});

module.exports = router;