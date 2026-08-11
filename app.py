from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from instagrapi import Client
import sqlite3
import os

app = FastAPI(title="Instagram Professional Panel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "database.db"

# Aapka Private Proxy URL Format
PROXY_URL = "http://ciiburkf:bx2e51jn04tc@191.96.254.138:6185"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            username TEXT PRIMARY KEY,
            password TEXT,
            coins INTEGER DEFAULT 2000,
            followers INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class LoginData(BaseModel):
    username: str
    password: str

class TaskData(BaseModel):
    accounts: List[str]
    target_user: str

# 1. Full Featured Frontend UI
@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Instagram Automation Panel</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body class="bg-blue-50 font-sans pb-24">

        <div class="bg-[#007bff] text-white p-4 flex justify-between items-center shadow-md">
            <div class="flex items-center space-x-2">
                <div class="w-10 h-10 rounded-full bg-white text-blue-600 flex items-center justify-center font-bold text-lg" id="avatar-letter">U</div>
                <div>
                    <span id="display-username" class="text-sm font-bold block">Instagram Panel</span>
                    <span id="ip-status" class="text-[10px] text-blue-200">Proxy Connected</span>
                </div>
            </div>
            <div class="bg-white text-yellow-600 px-3 py-1 rounded-full font-bold flex items-center space-x-1 shadow">
                <i class="fa-solid fa-coins text-yellow-500"></i>
                <span id="coin-balance">2000</span>
            </div>
        </div>

        <div class="max-w-md mx-auto p-4 space-y-4">
            <!-- Login Card -->
            <div class="bg-white p-5 rounded-2xl shadow-md">
                <h2 class="text-md font-bold text-gray-800 mb-3"><i class="fa-brands fa-instagram text-pink-600"></i> Login & Save Account</h2>
                <div class="space-y-3">
                    <input type="text" id="username" placeholder="Instagram Username" class="w-full p-3 border rounded-xl focus:outline-none focus:border-blue-500 text-sm">
                    <input type="password" id="password" placeholder="Instagram Password" class="w-full p-3 border rounded-xl focus:outline-none focus:border-blue-500 text-sm">
                    <button onclick="loginAcc()" class="w-full bg-[#007bff] text-white p-3 rounded-xl font-bold shadow hover:bg-blue-600 transition text-sm">Login via Proxy</button>
                </div>
                <p id="log-status" class="text-center text-xs mt-2 font-semibold"></p>
            </div>

            <!-- Task Card -->
            <div class="bg-white p-5 rounded-2xl shadow-md">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="font-bold text-gray-800 text-sm">Active Accounts List</h3>
                    <button onclick="loadAccounts()" class="text-blue-600 text-xs font-semibold"><i class="fa-solid fa-rotate"> Refresh</i></button>
                </div>
                <div id="acc-list" class="space-y-2 max-h-40 overflow-y-auto border p-2 rounded-xl bg-gray-50 mb-3">
                    <p class="text-xs text-gray-400 text-center py-2">Loading accounts...</p>
                </div>
                <div class="space-y-3">
                    <input type="text" id="target" placeholder="Target Username to Follow" class="w-full p-3 border rounded-xl text-sm focus:outline-none">
                    <button onclick="startTask()" class="w-full bg-green-600 text-white p-3 rounded-xl font-bold text-sm shadow hover:bg-green-700 transition">Start Follow Task</button>
                </div>
                <p id="task-status" class="text-center text-xs mt-2 font-semibold"></p>
            </div>
        </div>

        <script>
            async function loadAccounts() {
                try {
                    let res = await fetch('/api/accounts');
                    let data = await res.json();
                    let div = document.getElementById('acc-list');
                    div.innerHTML = '';
                    if(data.accounts.length === 0) {
                        div.innerHTML = '<p class="text-xs text-gray-400 text-center py-2">No accounts found.</p>';
                        return;
                    }
                    data.accounts.forEach(acc => {
                        div.innerHTML += `
                            <div class="flex items-center justify-between p-2 bg-white rounded-lg border">
                                <div class="flex items-center space-x-2">
                                    <input type="checkbox" class="acc-chk w-4 h-4" value="${acc.username}" checked>
                                    <span class="text-xs font-bold text-gray-700">${acc.username}</span>
                                </div>
                                <span class="text-xs text-yellow-600 font-semibold"><i class="fa-solid fa-coins"></i> ${acc.coins}</span>
                            </div>
                        `;
                    });
                } catch(e) { console.log(e); }
            }

            async function loginAcc() {
                let username = document.getElementById('username').value;
                let password = document.getElementById('password').value;
                let status = document.getElementById('log-status');
                
                if(!username || !password) {
                    status.innerText = "Please enter username and password!";
                    status.style.color = "red";
                    return;
                }

                status.innerText = "Logging in via Private Proxy...";
                status.style.color = "blue";
                
                try {
                    let res = await fetch('/api/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username, password})
                    });
                    let data = await res.json();
                    if(res.ok) {
                        status.innerText = "Login Success & Saved!";
                        status.style.color = "green";
                        document.getElementById('display-username').innerText = data.username;
                        document.getElementById('coin-balance').innerText = data.coins;
                        document.getElementById('avatar-letter').innerText = data.username.charAt(0).toUpperCase();
                        loadAccounts();
                    } else {
                        status.innerText = data.detail || "Login failed!";
                        status.style.color = "red";
                    }
                } catch(err) {
                    status.innerText = "Network error or timeout!";
                    status.style.color = "red";
                }
            }

            async function startTask() {
                let checkboxes = document.querySelectorAll('.acc-chk:checked');
                let accounts = Array.from(checkboxes).map(cb => cb.value);
                let target_user = document.getElementById('target').value;
                let status = document.getElementById('task-status');
                
                if(accounts.length === 0 || !target_user) {
                    status.innerText = "Select accounts and enter target user!";
                    status.style.color = "red";
                    return;
                }

                status.innerText = "Running follow task...";
                status.style.color = "blue";
                
                let res = await fetch('/api/start-task', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({accounts, target_user})
                });
                let data = await res.json();
                status.innerText = data.message;
                status.style.color = "green";
            }

            loadAccounts();
        </script>
    </body>
    </html>
    """

@app.get("/api/accounts")
def get_accounts():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username, coins, followers FROM accounts")
    rows = c.fetchall()
    conn.close()
    return {"accounts": [{"username": r[0], "coins": r[1], "followers": r[2]} for r in rows]}

@app.post("/api/login")
def login(data: LoginData):
    cl = Client()
    try:
        cl.set_proxy(PROXY_URL)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy setup error: {str(e)}")
    
    cl.set_device({"app_version": "330.0.0.38.118", "android_version": 34, "android_model": "Pixel 7", "android_device": "panther", "cpu": "gs201"})
    sf = f"session_{data.username}.json"
    
    try:
        if os.path.exists(sf):
            cl.load_settings(sf)
        
        cl.login(data.username, data.password)
        cl.dump_settings(sf)
        
        info = cl.user_info_by_username(data.username)
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''
            INSERT INTO accounts (username, password, coins, followers)
            VALUES (?, ?, 2000, ?)
            ON CONFLICT(username) DO UPDATE SET password=?, followers=?
        ''', (data.username, data.password, info.follower_count, data.password, info.follower_count))
        conn.commit()
        conn.close()
        
        return {"status": "success", "username": data.username, "coins": 2000}
    except Exception as e:
        err = str(e)
        if "challenge" in err.lower() or "two_factor" in err.lower():
            raise HTTPException(status_code=400, detail="Instagram 2FA/Checkpoint required. Login via official app.")
        raise HTTPException(status_code=400, detail=f"Login Error: {err}")

@app.post("/api/start-task")
def start_task(data: TaskData):
    count = 0
    for u in data.accounts:
        sf = f"session_{u}.json"
        if os.path.exists(sf):
            try:
                cl = Client()
                cl.set_proxy(PROXY_URL)
                cl.set_device({"app_version": "330.0.0.38.118", "android_version": 34, "android_model": "Pixel 7", "android_device": "panther", "cpu": "gs201"})
                cl.load_settings(sf)
                tid = cl.user_id_by_username(data.target_user)
                cl.user_follow(tid)
                count += 1
            except Exception as e:
                print(f"Task error for {u}:", e)
    return {"status": "success", "message": f"Successfully followed using {count} accounts!"}
