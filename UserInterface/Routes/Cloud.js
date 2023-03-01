const express = require("express");
var router = express.Router();

router.get('/', function (req, res, next){

   res.send("Cloud Device");

});







module.exports = router;