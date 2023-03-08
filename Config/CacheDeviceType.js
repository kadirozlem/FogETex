const fs = require('fs');
const readline = require('readline');

const FileDirectory = './Config/'

function SetDeviceType(deviceType) {
    const data = fs.readFileSync(FileDirectory + 'index.js',
        {encoding: 'utf8', flag: 'r'});

    const new_data = data.replace(/DeviceType: DeviceTypes.(\w+),/g, `DeviceType: DeviceTypes.${deviceType},`)

    fs.writeFileSync(FileDirectory + 'index.js', new_data, {encoding: "utf8", flag: 'w'});
    console.log(`Device type is setted as ${deviceType}!`)
}

function CacheDeviceType(deviceType) {
    fs.writeFileSync(FileDirectory + 'DeviceType.cache', deviceType, {encoding: "utf8", flag: 'w', mode: 0o644});
    SetDeviceType(deviceType);
}

function ReloadDeviceTypeFromCache() {
    if (fs.existsSync(FileDirectory + 'DeviceType.cache')) {
        const data = fs.readFileSync(FileDirectory + 'DeviceType.cache',
            {encoding: 'utf8', flag: 'r'});
        switch (data.trim().toLowerCase()) {
            case 'cloud':
                SetDeviceType('Cloud');
                break;
            case 'worker':
                SetDeviceType('Worker');
                break;
            case 'broker':
                SetDeviceType('Broker');
                break;
            default:
                console.log('ReloadDeviceTypeFromCache(): Device Type cannot found!');
        }
    } else {
        console.log('ReloadDeviceTypeFromCache(): Cache File cannot found!');
    }
}

function main(){
    if(process.argv.length>2){
        switch (process.argv[2].trim().toLowerCase()){
            case 'cloud':
                CacheDeviceType('Cloud');
                break;
            case 'worker':
                CacheDeviceType('Worker');
                break;
            case 'broker':
                CacheDeviceType('Broker');
                break;
            default:
                console.log('main(): Device Type cannot matched!');
        }
    }else{
        ReloadDeviceTypeFromCache();
    }
}
main();