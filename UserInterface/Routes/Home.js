const express = require("express");
var router = express.Router();

router.get('/', function (req, res, next){

    res.render('index',{title:"FogETex", user:"Kadir", deviceInfo:req.app.FogETex.DeviceInfo})
});

module.exports = router;