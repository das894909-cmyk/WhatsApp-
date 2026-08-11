from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from instagrapi import Client
import json
import os

app = FastAPI()

class LoginData(BaseModel):
    username: str
    password: str
    verification_code: str = None  # Agar Instagram OTP maange toh yeh use hoga

@app.post("/api/login")
def instagram_login(data: LoginData):
    cl = Client()
    
    try:
        # Agar pehle se session save hai toh load kar lo taaki baar-bar password na dena pade
        session_file = f"session_{data.username}.json"
        if os.path.exists(session_file):
            cl.load_settings(session_file)
            cl.login(data.username, data.password)
        else:
            if data.verification_code:
                # Agar user ne OTP daal diya hai
                cl.login(data.username, data.password, verification_code=data.verification_code)
            else:
                # Normal Username & Password login
                cl.login(data.username, data.password)
            
            # Login successful hone par session save kar lo
            cl.dump_settings(session_file)
            
        return {"status": "success", "message": f"Successfully logged in as {data.username}"}
        
    except Exception as e:
        error_msg = str(e)
        # Agar Instagram ne OTP ya Checkpoint maanga hai
        if "challenge" in error_msg.lower() or "two_factor" in error_msg.lower():
            return {"status": "otp_required", "message": "Instagram OTP or Verification required. Please send OTP."}
        
        raise HTTPException(status_code=400, detail=f"Login Failed: {error_msg}")