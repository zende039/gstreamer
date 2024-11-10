const io = require('socket.io-client');
const fs = require('fs');
const socket = io('http://15.181.49.61:3000');

socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('stream', (data) => {
    console.log('Received frame');
    const buffer = Buffer.from(data, 'base64');
    fs.writeFileSync('frame.jpg', buffer); // Save frame for testing
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
});

socket.on('connect_error', (err) => {
    console.error(`Connection error: ${err.message}`);
});

