const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const { spawn } = require('child_process');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

app.use(express.static(__dirname));

app.get('/', (req, res) => {
    res.sendFile(__dirname + '/index.html');
});

io.on('connection', (socket) => {
    console.log('Client connected.');

    const gst = spawn('gst-launch-1.0', [
        'udpsrc', 'address=15.181.49.61', 'port=5000', 'caps=application/x-rtp',
        '!', 'rtpvp8depay', '!', 'vp8dec', '!', 'videoconvert',
        '!', 'jpegenc', '!', 'fdsink'
    ]);

    gst.stdout.on('data', (data) => {
        socket.emit('stream', data.toString('base64'));
    });

    gst.stderr.on('data', (err) => {
        console.error(`GStreamer error: ${err}`);
    });

    gst.on('exit', (code) => {
        console.log(`GStreamer exited with code ${code}`);
    });

    socket.on('disconnect', () => {
        console.log('Client disconnected.');
        gst.kill();
    });
});

const PORT = 3000;
server.listen(PORT, () => {
    console.log(`Server is running on http://15.181.49.61:${PORT}`);
});

