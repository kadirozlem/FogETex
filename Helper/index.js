module.exports={
    DateTimeAsFilename:()=>{
        const date = new Date();
        const date_str= date.toLocaleDateString('tr-TR').split('.').reverse().join('_');
        const time_str =date.toLocaleTimeString('tr-TR').replace(/:/g,'_')
        return date_str+"_"+time_str;
    }





}