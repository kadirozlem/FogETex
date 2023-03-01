const express = require("express");
var router = express.Router();

router.get('/',  (req, res, next)=>{

   res.send("Cloud Device");

});

router.get('/GetBrokerIp',(req, res, next)=>{
   req.app.FogETex;
});






module.exports = router;