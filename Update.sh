git stash
git reset -- hard
git clean -fd
git pull
npm install
node ./Config/CacheDeviceType.js
#forever restart Server.js