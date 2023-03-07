const express = require("express");
const Helper = require("../../Helper");
var router = express.Router();

router.get('/',  (req, res, next)=>{

   res.send("Cloud Device");

});

router.get('/AssignFogNode',(req, res, next)=>{
   if(!req.query.lat && !req.query.lon){
      res.send('Missing Parameter');
   }

   const user_lat = parseFloat(req.query.lat);
   const user_lon = parseFloat(req.query.lon);
   const user_ip  = req.ip;

   const brokers = req.app.FogETex.Socket.fog_children;
   for (const key in brokers){
      if(brokers[key].deviceInfo.PublicIp == user_ip){
         res.json({IP: brokers[key].deviceInfo.PublicIp, err: null });
         return;
      }
   }

   const closest_node = null
   for (const key in brokers){


      if(brokers[key].deviceInfo.PublicIp == user_ip){
         res.json({IP: brokers[key].deviceInfo.PublicIp, err: null });
         return;
      }
   }





   req.app.FogETex;
   res.send(user_ip)
   //https://www.movable-type.co.uk/scripts/latlong.html
});

router.get('/GetBrokerIp',(req,res, next)=>{
   const user_ip  = req.ip;

   const brokers = req.app.FogETex.Socket.fog_children;
   for (const key in brokers){
      if(brokers[key].deviceInfo.PublicIp == user_ip){
         res.json({LocalIp: brokers[key].deviceInfo.PublicIp, err: null });
         return;
      }
   }
   res.json({LocalIp:null, err: "Broker device not yet connected!" })

});

module.exports = router;