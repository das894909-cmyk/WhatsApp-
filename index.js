const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const { makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const fs = require('fs');
const pino = require('pino');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

app.use(express.json());

let sessions = {};

// হোয়াটসঅ্যাপ কানেকশন ইঞ্জিন
async function startPairing(phoneNumber, socketId) {
    const id = "session_" + phoneNumber;
    const authPath = `./sessions/${id}`;
    const { state, saveCreds } = await useMultiFileAuthState(authPath);

    const sock = makeWASocket({
        auth: state,
        printQRInTerminal: false,
        logger: pino({ level: 'silent' }),
        browser: ["Ubuntu", "Chrome", "20.0.04"]
    });

    sock.ev.on('creds.update', saveCreds);

    if (!sock.authState.creds.registered) {
        setTimeout(async () => {
            try {
                const code = await sock.requestPairingCode(phoneNumber);
                io.to(socketId).emit('pairing-code', { code });
            } catch (err) {
                io.to(socketId).emit('error', 'কোড তৈরি করা যায়নি।');
            }
        }, 3000);
    }

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect } = update;
        if (connection === 'open') {
            sessions[id] = { sock, number: phoneNumber, loginTime: Date.now(), id };
            io.emit('session-update', getSessionList());
            io.to(socketId).emit('link-success');
        }
        if (connection === 'close') {
            const shouldReconnect = lastDisconnect.error?.output?.statusCode !== DisconnectReason.loggedOut;
            if (shouldReconnect) startPairing(phoneNumber, socketId);
            else {
                delete sessions[id];
                if (fs.existsSync(authPath)) fs.rmSync(authPath, { recursive: true });
                io.emit('session-update', getSessionList());
            }
        }
    });
}

function getSessionList() {
    return Object.values(sessions).map(s => ({
        id: s.id, number: s.number, uptime: Math.floor((Date.now() - s.loginTime) / 1000)
    }));
}

// APIs
app.get('/api/sessions', (req, res) => res.json(getSessionList()));

app.post('/api/logout', (req, res) => {
    const { id } = req.body;
    if (sessions[id]) { sessions[id].sock.logout(); res.json({ success: true }); }
});

app.post('/api/broadcast', async (req, res) => {
    const { message, targets, delay } = req.body;
    const sKeys = Object.keys(sessions);
    if (sKeys.length === 0) return res.json({ error: "No device" });
    res.json({ status: "Started" });
    for (let i = 0; i < targets.length; i++) {
        const session = sessions[sKeys[i % sKeys.length]];
        try { await session.sock.sendMessage(targets[i].trim() + "@s.whatsapp.net", { text: message }); } catch (e) {}
        await new Promise(r => setTimeout(r, delay * 1000));
    }
});

// মেইন ড্যাশবোর্ড HTML (Frontend)
app.get('/', (req, res) => {
    res.send(`
<!DOCTYPE html>
<html>
<head>
    <title>WhatsApp Multi-Device Manager</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; background: #f0f2f5; margin: 0; }
        .nav { background: #075e54; color: white; padding: 15px; display: flex; gap: 20px; }
        .nav b { cursor: pointer; padding: 5px 10px; }
        .nav b:hover { background: #128c7e; border-radius: 5px; }
        .container { padding: 20px; max-width: 800px; margin: auto; }
        .page { display: none; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .active { display: block; }
        input, textarea, button { width: 100%; padding: 12px; margin-top: 10px; box-sizing: border-box; border-radius: 5px; border: 1px solid #ddd; }
        button { background: #25d366; color: white; font-weight: bold; border: none; cursor: pointer; }
        .code-display { font-size: 35px; text-align: center; color: #075e54; letter-spacing: 5px; margin: 20px; font-weight: bold; }
        .device-card { border: 1px solid #eee; padding: 15px; margin-top: 10px; display: flex; justify-content: space-between; align-items: center; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="nav">
        <b onclick="showPage('link')">Link Device</b>
        <b onclick="showPage('devices')">Connected Devices</b>
        <b onclick="showPage('broadcast')">Send Broadcast</b>
    </div>

    <div class="container">
        <div id="link" class="page active">
            <h2>🔗 Link WhatsApp (OTP Code)</h2>
            <input type="text" id="phone" placeholder="নম্বর দিন (যেমন: 919876543210)">
            <button onclick="getPairingCode()">লিঙ্ক কোড জেনারেট করুন</button>
            <div id="code-status"></div>
            <div class="code-display" id="pairing-code">--------</div>
        </div>

        <div id="devices" class="page">
            <h2>✅ কানেক্টেড ডিভাইসসমূহ</h2>
            <div id="device-list">লোডিং...</div>
        </div>

        <div id="broadcast" class="page">
            <h2>📤 ব্রডকাস্ট প্যানেল</h2>
            <textarea id="msg" placeholder="আপনার মেসেজ লিখুন..." rows="4"></textarea>
            <textarea id="nums" placeholder="নম্বরগুলো কমা দিয়ে দিন (উদা: 91...,91...)"></textarea>
            <input type="number" id="delay" value="10" title="Delay in seconds">
            <button onclick="sendBroadcast()" style="background:#007bff">মেসেজ পাঠানো শুরু করুন</button>
        </div>
    </div>

    <script src="/socket.io/socket.io.js"></script>
    <script>
        const socket = io();
        function showPage(id) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            if(id === 'devices') loadDevices();
        }

        function getPairingCode() {
            const num = document.getElementById('phone').value;
            if(!num) return alert("নম্বর দিন!");
            socket.emit('request-pairing', { number: num });
            document.getElementById('code-status').innerText = "আপনার হোয়াটসঅ্যাপে গিয়ে Link with Phone Number সিলেক্ট করুন...";
        }

        socket.on('pairing-code', (data) => {
            document.getElementById('pairing-code').innerText = data.code;
        });

        socket.on('link-success', () => {
            alert("ডিভাইস লিঙ্ক হয়েছে!");
            showPage('devices');
        });

        async function loadDevices() {
            const res = await fetch('/api/sessions');
            const data = await res.json();
            document.getElementById('device-list').innerHTML = data.map(s => \`
                <div class="device-card">
                    <div><b>\${s.number}</b><br><small>অনলাইন: \${Math.floor(s.uptime/60)} মিনিট</small></div>
                    <button onclick="logout('\${s.id}')" style="width:auto; background:red;">Logout</button>
                </div>
            \`).join('') || "কোন ডিভাইস কানেক্টেড নেই।";
        }

        async function logout(id) {
            await fetch('/api/logout', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id}) });
            loadDevices();
        }

        async function sendBroadcast() {
            const payload = {
                message: document.getElementById('msg').value,
                targets: document.getElementById('nums').value.split(','),
                delay: document.getElementById('delay').value
            };
            await fetch('/api/broadcast', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload) });
            alert("মেসেজ পাঠানো শুরু হয়েছে!");
        }
    </script>
</body>
</html>
    `);
});

io.on('connection', (socket) => {
    socket.on('request-pairing', (data) => startPairing(data.number, socket.id));
});

server.listen(3000, () => console.log('Server is online at port 3000'));