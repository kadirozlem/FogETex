const express = require("express");
const Config = require("../../Config");
const router = express.Router();

router.get('/', function (req, res, next){

    res.render('index',{title:"FogETex", UserType:Config.DeviceTypes.UserInterface, DeviceInfo:req.app.FogETex.DeviceInfo,Directory: 'Home'})
});

module.exports = router;