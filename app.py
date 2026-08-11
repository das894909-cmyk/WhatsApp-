from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from instagrapi import Client
import os

app = FastAPI(title="Instagram Panel App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    username: str
    password: str

# 1. Pura App ka UI (HTML/CSS/JS) jo website khulte hi dikhega
@app.get("/", response_class=HTMLResponse)
def home_page():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Instagram Follower Panel</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body class="bg-blue-50 font-sans pb-20">

        <!-- Top Header -->
        <div class="bg-[#007bff] text-white p-4 flex justify-between items-center shadow-md">
            <div class="flex items-center space-x-2">
                <img id="user-avatar" src="https://via.placeholder.com/40" class="w-10 h-10 rounded-full border-2 border-white object-cover" alt="Profile">
                <div>
                    <span id="display-username" class="text-sm font-bold block">Not Logged In</span>
                </div>
            </div>
            <div class="bg-white text-yellow-600 px-3 py-1 rounded-full font-bold flex items-center space-x-1 shadow">
                <i class="fa-solid fa-coins text-yellow-500"></i>
                <span id="coin-balance">18627</span>
            </div>
        </div>

        <!-- Main Container -->
        <div class="max-w-md mx-auto p-4">

            <!-- Login Section / Card -->
            <div id="login-card" class="bg-white p-6 rounded-2xl shadow-md mt-4">
                <h2 class="text-lg font-bold text-gray-800 mb-4 text-center"><i class="fa-brands fa-instagram text-pink-600"></i> Connect Instagram Account</h2>
                <div class="space-y-3">
                    <input type="text" id="username" placeholder="Instagram Username" class="w-full p-3 border rounded-xl focus:outline-none focus:border-blue-500">
                    <input type="password" id="password" placeholder="Instagram Password" class="w-full p-3 border rounded-xl focus:outline-none focus:border-blue-500">
                    <button onclick="loginUser()" class="w-full bg-[#007bff] text-white p-3 rounded-xl font-bold shadow-lg hover:bg-blue-600 transition">Login & Connect</button>
                </div>
                <p id="login-status" class="text-center text-sm mt-3 text-gray-600"></p>
            </div>

            <!-- Dashboard Options (Hidden initially until login, or shown as template) -->
            <div id="dashboard-menu" class="mt-4 space-y-3">
                <div class="bg-white p-4 rounded-xl shadow-sm flex justify-between items-center cursor-pointer hover:bg-gray-50">
                    <div class="flex items-center space-x-3 text-blue-600">
                        <i class="fa-solid fa-file-invoice text-xl"></i>
                        <span class="font-semibold text-gray-700">Submit Orders</span>
                    </div>
                    <i class="fa-solid fa-chevron-right text-gray-400"></i>
                </div>

                <div class="bg-white p-4 rounded-xl shadow-sm flex justify-between items-center cursor-pointer hover:bg-gray-50">
                    <div class="flex items-center space-x-3 text-blue-600">
                        <i class="fa-solid fa-cart-shopping text-xl"></i>
                        <span class="font-semibold text-gray-700">Order For Others</span>
                    </div>
                    <i class="fa-solid fa-chevron-right text-gray-400"></i>
                </div>

                <div class="bg-white p-4 rounded-xl shadow-sm flex justify-between items-center cursor-pointer hover:bg-gray-50">
                    <div class="flex items-center space-x-3 text-blue-600">
                        <i class="fa-solid fa-crown text-xl"></i>
                        <span class="font-semibold text-gray-700">Upgrade Your Account</span>
                    </div>
                    <i class="fa-solid fa-chevron-right text-gray-400"></i>
                </div>

                <div class="bg-white p-4 rounded-xl shadow-sm flex justify-between items-center cursor-pointer hover:bg-gray-50">
                    <div class="flex items-center space-x-3 text-blue-600">
                        <i class="fa-solid fa-gift text-xl"></i>
                        <span class="font-semibold text-gray-700">Free Coins</span>
                    </div>
                    <i class="fa-solid fa-chevron-right text-gray-400"></i>
                </div>

                <div class="bg-white p-4 rounded-xl shadow-sm flex justify-between items-center cursor-pointer hover:bg-gray-50">
                    <div class="flex items-center space-x-3 text-blue-600">
                        <i class="fa-solid fa-right-left text-xl"></i>
                        <span class="font-semibold text-gray-700">Transfer Coin</span>
                    </div>
                    <i class="fa-solid fa-chevron-right text-gray-400"></i>
                </div>

                <div class="bg-white p-4 rounded-xl shadow-sm flex justify-between items-center cursor-pointer hover:bg-gray-50">
                    <div class="flex items-center space-x-3 text-blue-600">
                        <i class="fa-solid fa-user-plus text-xl"></i>
                        <span class="font-semibold text-gray-700">Invite Friends</span>
                    </div>
                    <span class="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full font-bold">New</span>
                </div>
            </div>

        </div>

        <!-- Bottom Navigation Bar -->
        <div class="fixed bottom-0 left-0 right-0 bg-white border-t flex justify-around py-3 shadow-lg">
            <button class="flex flex-col items-center text-blue-600 font-bold">
                <i class="fa-solid fa-house text-xl"></i>
                <span class="text-xs mt-1">Home</span>
            </button>
            <button class="flex flex-col items-center text-gray-400 hover:text-blue-600">
                <i class="fa-solid fa-coins text-xl"></i>
                <span class="text-xs mt-1">Get Coin</span>
            </button>
            <button class="flex flex-col items-center text-gray-400 hover:text-blue-600">
                <i class="fa-solid fa-user-check text-xl"></i>
                <span class="text-xs mt-1">Get Follower</span>
            </button>
        </div>

        <!-- JavaScript for Login API Connection -->
        <script>
            async function loginUser() {
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const statusEl = document.getElementById('login-status');

                if(!username || !password) {
                    statusEl.innerText = "Please enter both username and password!";
                    statusEl.style.color = "red";
                    return;
                }

                statusEl.innerText = "Logging in... Please wait...";
                statusEl.style.color = "blue";

                try {
                    const response = await fetch('/api/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username, password })
                    });

                    const data = await response.json();

                    if(response.ok) {
                        statusEl.innerText = "Login Successful!";
                        statusEl.style.color = "green";
                        document.getElementById('display-username').innerText = data.username;
                        document.getElementById('coin-balance').innerText = "2000"; // Starting coins
                    } else {
                        statusEl.innerText = data.detail || "Login failed!";
                        statusEl.style.color = "red";
                    }
                } catch (err) {
                    statusEl.innerText = "Connection error!";
                    statusEl.style.color = "red";
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content

# 2. Backend API Endpoint for Login
@app.post("/api/login")
def login_instagram(data: LoginRequest):
    cl = Client()
    session_file = f"session_{data.username}.json"
    
    try:
        if os.path.exists(session_file):
            cl.load_settings(session_file)
        
        cl.login(data.username, data.password)
        cl.dump_settings(session_file)
        
        user_info = cl.user_info_by_username(data.username)
        
        return {
            "status": "success",
            "message": f"Successfully logged in as {data.username}",
            "username": data.username,
            "followers": user_info.follower_count,
            "following": user_info.following_count
        }
        
    except Exception as e:
        error_message = str(e)
        if "challenge" in error_message.lower() or "two_factor" in error_message.lower():
            raise HTTPException(
                status_code=400, 
                detail="Instagram security checkpoint or 2FA required. Try logging in via official app first."
            )
        raise HTTPException(status_code=400, detail=f"Login failed: {error_message}")
