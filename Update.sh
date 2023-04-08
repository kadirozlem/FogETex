git stash
git reset -- hard
git clean -fd
git pull
npm install
node ./Config/CacheDeviceType.js
forever restart Server.js
forever restart LoadTest/FogETexResourceManager/index.js
cd GaitAnalysis
forever restart -c "python main.py"