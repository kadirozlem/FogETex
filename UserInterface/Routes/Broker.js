const express = require("express");
var router = express.Router();

router.get('/', function (req, res, next){

   res.send("Broker Device");
});

router.get('/AssignWorkerDevice', function (req, res, next){

});






module.exports = router;