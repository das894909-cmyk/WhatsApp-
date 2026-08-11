from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from instagrapi import Client
import sqlite3
import requests
import os
import itertools

app = FastAPI(title="Instagram Panel App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "database.db"

# Geonode Proxy Pool Fetcher with error handling
def fetch_proxies():
    proxy_list = []
    try:
        url = "https://proxylist.geonode.com/api/proxy-list?page=1&limit=50&sort_by=responseTime&sort_type=asc"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            data = res.json()
            for item in data.get("data", []):
                ip = item.get("ip")
                port = item.get("port")
                protos = item.get("protocols", ["http"])
                proto = protos[0] if protos else "http"
                if ip and port:
                    proxy_list.append(f"{proto}://{ip}:{port}")
    except Exception as e:
        print("Proxy fetch error:", e)
    return proxy_list

PROXY_POOL = itertools.cycle(fetch_proxies() or ["http://31.59.20.176:6754"])

def get_proxy():
    try:
        return next(PROXY_POOL)
    except:
        return None

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

# HTML UI
@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Instagram Panel</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body class="bg-gray-100 p-4">
        <div class="max-w-md mx-auto bg-white rounded-xl shadow-md p-6 space-y-4">
            <h1 class="text-xl font-bold text-center text-blue-600"><i class="fa-brands fa-instagram"></i> Instagram Automation</h1>
            
            <div class="space-y-2">
                <input type="text" id="username" placeholder="Username" class="w-full p-2 border rounded">
                <input type="password" id="password" placeholder="Password" class="w-full p-2 border rounded">
                <button onclick="loginAcc()" class="w-full bg-blue-500 text-white p-2 rounded font-bold">Login & Save</button>
                <p id="log-status" class="text-xs text-center font-semibold"></p>
            </div>

            <hr>

            <div class="space-y-2">
                <h3 class="font-bold text-sm">Accounts List</h3>
                <div id="acc-list" class="max-h-32 overflow-y-auto border p-2 rounded text-xs">Loading...</div>
                <input type="text" id="target" placeholder="Target Username" class="w-full p-2 border rounded">
                <button onclick="startTask()" class="w-full bg-green-500 text-white p-2 rounded font-bold">Start Follow Task</button>
                <p id="task-status" class="text-xs text-center font-semibold"></p>
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
                        div.innerHTML = 'No accounts found';
                        return;
                    }
                    data.accounts.forEach(acc => {
                        div.innerHTML += `<label class="block mb-1"><input type="checkbox" class="acc-chk" value="${acc.username}" checked> ${acc.username} (Coins: ${acc.coins})</label>`;
                    });
                } catch(e) { console.log(e); }
            }

            async function loginAcc() {
                let username = document.getElementById('username').value;
                let password = document.getElementById('password').value;
                let status = document.getElementById('log-status');
                
                if(!username || !password) {
                    status.innerText = "Enter username and password!";
                    status.style.color = "red";
                    return;
                }

                status.innerText = "Logging in... Please wait.";
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
                    status.innerText = "Select accounts and enter target!";
                    status.style.color = "red";
                    return;
                }

                status.innerText = "Running task...";
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
    # Direct login without blocking proxy to ensure it doesn't freeze
    cl.set_device({"app_version": "330.0.0.38.118", "android_version": 34, "android_model": "Pixel 7", "android_device": "panther", "cpu": "gs201"})
    session_file = f"session_{data.username}.json"
    
    try:
        if os.path.exists(session_file):
            cl.load_settings(session_file)
        
        cl.login(data.username, data.password)
        cl.dump_settings(session_file)
        
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
        
        return {"status": "success", "username": data.username}
    except Exception as e:
        error_msg = str(e)
        if "challenge" in error_msg.lower() or "two_factor" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Instagram 2FA/Checkpoint required. Login via official app first.")
        raise HTTPException(status_code=400, detail=f"Login Error: {error_msg}")

@app.post("/api/start-task")
def start_task(data: TaskData):
    count = 0
    for u in data.accounts:
        sf = f"session_{u}.json"
        if os.path.exists(sf):
            try:
                cl = Client()
                p = get_proxy()
                if p:
                    try:
                        cl.set_proxy(p)
                    except:
                        pass
                cl.set_device({"app_version": "330.0.0.38.118", "android_version": 34, "android_model": "Pixel 7", "android_device": "panther", "cpu": "gs201"})
                cl.load_settings(sf)
                tid = cl.user_id_by_username(data.target_user)
                cl.user_follow(tid)
                count += 1
            except Exception as e:
                print("Task error:", e)
    return {"status": "success", "message": f"Completed for {count} accounts!"}
