forever stopall
forever start Server.js
forever start LoadTest/FogETexResourceManager/index.js
cd GaitAnalysis
forever start -c python main.py
forever start -c python main.py
forever start -c python main.py
forever start -c python main.py
cd ..