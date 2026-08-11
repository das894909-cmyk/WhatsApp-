from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from instagrapi import Client
import os
import json

app = FastAPI(title="Instagram Panel Backend")

# CORS enable karna zaroori hai taaki aapka app/frontend isse connect ho sake
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

@app.get("/")
def home():
    return {"status": "success", "message": "Instagram Automation Backend is Live and Running!"}

@app.post("/api/login")
def login_instagram(data: LoginRequest):
    cl = Client()
    session_file = f"session_{data.username}.json"
    
    try:
        # Agar pehle se session save hai toh load karne ki koshish karo
        if os.path.exists(session_file):
            cl.load_settings(session_file)
        
        # Instagram login process
        cl.login(data.username, data.password)
        
        # Successful login ke baad session save kar lo
        cl.dump_settings(session_file)
        
        # User ki basic details nikalna (jaise profile stats)
        user_info = cl.user_info_by_username(data.username)
        
        return {
            "status": "success",
            "message": f"Successfully logged in as {data.username}",
            "username": data.username,
            "followers": user_info.follower_count,
            "following": user_info.following_count,
            "posts": user_info.media_count
        }
        
    except Exception as e:
        error_message = str(e)
        if "challenge" in error_message.lower() or "two_factor" in error_message.lower():
            raise HTTPException(
                status_code=400, 
                detail="Instagram ne security check ya 2FA maanga hai. Pehle official app mein login karke check karein."
            )
        raise HTTPException(status_code=400, detail=f"Login failed: {error_message}")
