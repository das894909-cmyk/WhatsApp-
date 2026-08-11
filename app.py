from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from instagrapi import Client
import sqlite3
import os

app = FastAPI(title="Instagram Panel App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "database.db"

# Aapka Private Proxy Details
PROXY_HOST = "191.96.254.138"
PROXY_PORT = "6185"
PROXY_USER = "ciiburkf"
PROXY_PASS = "bx2e51jn04tc"

# Proxy String Helper
def get_proxy_string():
    return f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"

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
    </head>
    <body class="bg-gray-100 p-4">
        <div class="max-w-md mx-auto bg-white rounded-xl shadow-md p-6 space-y-4">
            <h1 class="text-xl font-bold text-center text-blue-600">Instagram Login</h1>
            <input type="text" id="username" placeholder="Username" class="w-full p-2 border rounded">
            <input type="password" id="password" placeholder="Password" class="w-full p-2 border rounded">
            <button onclick="loginAcc()" class="w-full bg-blue-500 text-white p-2 rounded">Login & Save</button>
            <p id="log-status" class="text-xs text-center"></p>
            <hr>
            <div id="acc-list" class="text-xs"></div>
            <input type="text" id="target" placeholder="Target User" class="w-full p-2 border rounded">
            <button onclick="startTask()" class="w-full bg-green-500 text-white p-2 rounded">Start Follow</button>
        </div>
        <script>
            async function loadAccounts() {
                let res = await fetch('/api/accounts');
                let data = await res.json();
                document.getElementById('acc-list').innerHTML = data.accounts.map(a => 
                    `<label class="block"><input type="checkbox" class="acc-chk" value="${a.username}" checked> ${a.username}</label>`
                ).join('');
            }
            async function loginAcc() {
                let status = document.getElementById('log-status');
                status.innerText = "Connecting via Proxy...";
                let res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: document.getElementById('username').value, password: document.getElementById('password').value})
                });
                if(res.ok) { status.innerText = "Login Success!"; loadAccounts(); }
                else { status.innerText = "Login Failed"; }
            }
            async function startTask() {
                let accs = Array.from(document.querySelectorAll('.acc-chk:checked')).map(cb => cb.value);
                await fetch('/api/start-task', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({accounts: accs, target_user: document.getElementById('target').value})
                });
                alert("Task Started!");
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
    c.execute("SELECT username, coins FROM accounts")
    rows = c.fetchall()
    conn.close()
    return {"accounts": [{"username": r[0], "coins": r[1]} for r in rows]}

@app.post("/api/login")
def login(data: LoginData):
    cl = Client()
    cl.set_proxy(get_proxy_string()) # Proxy set ho gaya
    cl.set_device({"app_version": "330.0.0.38.118", "android_version": 34, "android_model": "Pixel 7", "android_device": "panther", "cpu": "gs201"})
    
    sf = f"session_{data.username}.json"
    if os.path.exists(sf): cl.load_settings(sf)
    
    cl.login(data.username, data.password)
    cl.dump_settings(sf)
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO accounts (username, password) VALUES (?, ?)", (data.username, data.password))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/start-task")
def start_task(data: TaskData):
    for u in data.accounts:
        cl = Client()
        cl.set_proxy(get_proxy_string()) # Task mein bhi Proxy
        cl.set_device({"app_version": "330.0.0.38.118", "android_version": 34, "android_model": "Pixel 7", "android_device": "panther", "cpu": "gs201"})
        cl.load_settings(f"session_{u}.json")
        tid = cl.user_id_by_username(data.target_user)
        cl.user_follow(tid)
    return {"status": "success"}
