git stash
git reset -- hard
git clean -fd
git pull --recurse-submodules
npm install
cd ./
node ./Config/CacheDeviceType.js
forever restart Server.js
forever restart LoadTest/FogETexResourceManager/index.js
cd GaitAnalysis
forever restart -c python main.py
cd ..