import socketio


sio = socketio.Client()
sio.connect('http://localhost:27592?DeviceType=3')