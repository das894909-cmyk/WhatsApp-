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

app = FastAPI(title="Instagram Panel App with Geonode Proxies")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "database.db"
IPSTACK_KEY = "dcdfb3fe0dee0ca472518a429aeb8b4e"

# Geonode API se live proxies fetch karne ka function
def fetch_geonode_proxies():
    proxy_list = []
    api_url = "https://proxylist.geonode.com/api/proxy-list?page=1&limit=500&sort_by=responseTime&sort_type=asc"
    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            for item in data.get("data", []):
                ip = item.get("ip")
                port = item.get("port")
                protocols = item.get("protocols", ["http"])
                protocol = protocols[0] if protocols else "http"
                if ip and port:
                    proxy_str = f"{protocol}://{ip}:{port}"
                    proxy_list.append(proxy_str)
    except Exception as e:
        print(f"Error fetching proxies from Geonode API: {e}")
    
    # Fallback proxies agar API fail ho jaye taaki app crash na ho
    if not proxy_list:
        proxy_list = [
            "http://31.59.20.176:6754",
            "http://45.38.107.97:6014"
        ]
    
    return proxy_list

# Proxies load karke cycle pool banana
PROXY_LIST = fetch_geonode_proxies()
proxy_pool = itertools.cycle(PROXY_LIST)

def get_next_proxy():
    try:
        return next(proxy_pool)
    except Exception:
        return None

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            username TEXT PRIMARY KEY,
            password TEXT,
            coins INTEGER DEFAULT 2000,
            followers INTEGER DEFAULT 0,
            following INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class LoginRequest(BaseModel):
    username: str
    password: str

class BatchTaskRequest(BaseModel):
    accounts: List[str]
    target_user: str

# 1. Frontend UI
@app.get("/", response_class=HTMLResponse)
def home_page():
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Instagram Follower Panel</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body class="bg-blue-50 font-sans pb-24">

        <div class="bg-[#007bff] text-white p-4 flex justify-between items-center shadow-md">
            <div class="flex items-center space-x-2">
                <div class="w-10 h-10 rounded-full bg-white text-blue-600 flex items-center justify-center font-bold text-lg" id="avatar-letter">U</div>
                <div>
                    <span id="display-username" class="text-sm font-bold block">No Account Connected</span>
                    <span id="ip-status" class="text-[10px] text-blue-200">Checking IP...</span>
                </div>
            </div>
            <div class="bg-white text-yellow-600 px-3 py-1 rounded-full font-bold flex items-center space-x-1 shadow">
                <i class="fa-solid fa-coins text-yellow-500"></i>
                <span id="coin-balance">0</span>
            </div>
        </div>

        <div class="max-w-md mx-auto p-4 space-y-4">
            <div class="bg-white p-5 rounded-2xl shadow-md">
                <h2 class="text-md font-bold text-gray-800 mb-3"><i class="fa-brands fa-instagram text-pink-600"></i> Add / Login Account</h2>
                <div class="space-y-3">
                    <input type="text" id="username" placeholder="Instagram Username" class="w-full p-3 border rounded-xl focus:outline-none focus:border-blue-500 text-sm">
                    <input type="password" id="password" placeholder="Instagram Password" class="w-full p-3 border rounded-xl focus:outline-none focus:border-blue-500 text-sm">
                    <button onclick="loginUser()" class="w-full bg-[#007bff] text-white p-3 rounded-xl font-bold shadow hover:bg-blue-600 transition text-sm">Login & Save Account</button>
                </div>
                <p id="login-status" class="text-center text-xs mt-2 text-gray-600"></p>
            </div>

            <div class="bg-white p-5 rounded-2xl shadow-md">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="font-bold text-gray-800 text-sm">Choose Accounts (Active)</h3>
                    <button onclick="loadAccounts()" class="text-blue-600 text-xs font-semibold"><i class="fa-solid fa-rotate"> Refresh</i></button>
                </div>
                <div id="accounts-list" class="space-y-2 max-h-40 overflow-y-auto">
                    <p class="text-xs text-gray-400 text-center py-2">No accounts loaded yet.</p>
                </div>
                <div class="mt-3">
                    <input type="text" id="target-user" placeholder="Target Username to Follow" class="w-full p-3 border rounded-xl text-sm mb-2 focus:outline-none">
                    <button onclick="startAutomation()" class="w-full bg-green-600 text-white p-3 rounded-xl font-bold text-sm shadow hover:bg-green-700 transition">Start Automation</button>
                </div>
                <p id="task-status" class="text-center text-xs mt-2 text-gray-600"></p>
            </div>
        </div>

        <script>
            async function checkMyIP() {
                try {
                    const res = await fetch('/api/check-ip');
                    const data = await res.json();
                    document.getElementById('ip-status').innerText = `IP: ${{data.ip}} (${{data.city}}, ${{data.country}})`;
                } catch(e) {
                    document.getElementById('ip-status').innerText = "IP check failed";
                }
            }
            checkMyIP();

            async function loginUser() {
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const statusEl = document.getElementById('login-status');

                if(!username || !password) {
                    statusEl.innerText = "Please enter username and password!";
                    statusEl.style.color = "red";
                    return;
                }

                statusEl.innerText = "Logging in & saving to database...";
                statusEl.style.color = "blue";

                try {
                    const response = await fetch('/api/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username, password })
                    });
                    const data = await response.json();
                    if(response.ok) {
                        statusEl.innerText = "Login Successful & Saved!";
                        statusEl.style.color = "green";
                        document.getElementById('display-username').innerText = data.username;
                        document.getElementById('coin-balance').innerText = data.coins;
                        document.getElementById('avatar-letter').innerText = data.username.charAt(0).toUpperCase();
                        loadAccounts();
                    } else {
                        statusEl.innerText = data.detail || "Login failed!";
                        statusEl.style.color = "red";
                    }
                } catch (err) {
                    statusEl.innerText = "Server error!";
                    statusEl.style.color = "red";
                }
            }

            async function loadAccounts() {
                try {
                    const res = await fetch('/api/accounts');
                    const data = await res.json();
                    const listEl = document.getElementById('accounts-list');
                    listEl.innerHTML = "";
                    if(data.accounts.length === 0) {
                        listEl.innerHTML = '<p class="text-xs text-gray-400 text-center py-2">No accounts found.</p>';
                        return;
                    }
                    data.accounts.forEach(acc => {
                        listEl.innerHTML += `
                            <div class="flex items-center justify-between p-2 bg-gray-50 rounded-lg border">
                                <div class="flex items-center space-x-2">
                                    <input type="checkbox" class="acc-checkbox w-4 h-4" value="${{acc.username}}" checked>
                                    <span class="text-xs font-bold text-gray-700">${{acc.username}}</span>
                                </div>
                                <span class="text-xs text-yellow-600 font-semibold"><i class="fa-solid fa-coins"></i> ${{acc.coins}}</span>
                            </div>
                        `;
                    });
                } catch(e) { console.log(e); }
            }

            async function startAutomation() {
                const checkboxes = document.querySelectorAll('.acc-checkbox:checked');
                const accounts = Array.from(checkboxes).map(cb => cb.value);
                const targetUser = document.getElementById('target-user').value;
                const taskStatus = document.getElementById('task-status');

                if(accounts.length === 0 || !targetUser) {
                    taskStatus.innerText = "Select at least one account and enter target user!";
                    taskStatus.style.color = "red";
                    return;
                }

                taskStatus.innerText = "Running automation on selected accounts...";
                taskStatus.style.color = "blue";

                const res = await fetch('/api/start-task', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ accounts, target_user: targetUser })
                });
                const data = await res.json();
                taskStatus.innerText = data.message;
                taskStatus.style.color = "green";
            }

            loadAccounts();
        </script>
    </body>
    </html>
    """

# 2. API: Check IP
@app.get("/api/check-ip")
def check_ip():
    try:
        url = f"http://api.ipstack.com/check?access_key={IPSTACK_KEY}"
        response = requests.get(url, timeout=5)
        data = response.json()
        return {
            "ip": data.get("ip", "Unknown"),
            "city": data.get("city", "Unknown"),
            "country": data.get("country_name", "Unknown")
        }
    except Exception as e:
        return {"ip": "Error", "city": str(e), "country": ""}

# 3. API: Login
@app.post("/api/login")
def login_instagram(data: LoginRequest):
    cl = Client()
    try:
        proxy = get_next_proxy()
        if proxy:
            cl.set_proxy(proxy)
    except Exception as e:
        print(f"Proxy setting failed: {e}")

    cl.set_device({"app_version": "330.0.0.38.118", "android_version": 34, "android_model": "Pixel 7", "android_device": "panther", "cpu": "gs201"})
    session_file = f"session_{data.username}.json"
    
    try:
        if os.path.exists(session_file):
            cl.load_settings(session_file)
        
        cl.login(data.username, data.password)
        cl.dump_settings(session_file)
        
        user_info = cl.user_info_by_username(data.username)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO accounts (username, password, coins, followers, following)
            VALUES (?, ?, 2000, ?, ?)
            ON CONFLICT(username) DO UPDATE SET password=?, followers=?, following=?
        ''', (data.username, data.password, user_info.follower_count, user_info.following_count, 
              data.password, user_info.follower_count, user_info.following_count))
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "username": data.username,
            "coins": 2000,
            "followers": user_info.follower_count
        }
    except Exception as e:
        error_msg = str(e)
        if "challenge" in error_msg.lower() or "two_factor" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Instagram 2FA/Checkpoint required. Please login via official app first.")
        raise HTTPException(status_code=400, detail=f"Login failed: {error_msg}")

# 4. API: Get Accounts
@app.get("/api/accounts")
def get_accounts():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT username, coins, followers FROM accounts")
    rows = cursor.fetchall()
    conn.close()
    
    accounts = [{"username": r[0], "coins": r[1], "followers": r[2]} for r in rows]
    return {"accounts": accounts}

# 5. API: Start Task
@app.post("/api/start-task")
def start_task(data: BatchTaskRequest):
    success_count = 0
    for username in data.accounts:
        session_file = f"session_{username}.json"
        if os.path.exists(session_file):
            try:
                cl = Client()
                try:
                    proxy = get_next_proxy()
                    if proxy:
                        cl.set_proxy(proxy)
                except Exception as proxy_err:
                    print(f"Proxy error for task: {proxy_err}")

                cl.set_device({"app_version": "330.0.0.38.118", "android_version": 34, "android_model": "Pixel 7", "android_device": "panther", "cpu": "gs201"})
                cl.load_settings(session_file)
                target_id = cl.user_id_by_username(data.target_user)
                cl.user_follow(target_id)
                success_count += 1
            except Exception as e:
                print(f"Error for {username}: {str(e)}")
                
    return {"status": "success", "message": f"Successfully completed task for {success_count} accounts!"}
