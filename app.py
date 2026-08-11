@app.post("/api/login")
def login(data: LoginData):
    cl = Client()
    
    # Try connecting with proxy, if it fails, fallback or raise clear error
    try:
        cl.set_proxy(PROXY_URL)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy Connection Refused: {str(e)}")
    
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
        if "timeout" in err.lower() or "connection" in err.lower():
            raise HTTPException(status_code=400, detail="Proxy Timeout! Proxy server respond nahi kar raha hai.")
        if "challenge" in err.lower() or "two_factor" in err.lower():
            raise HTTPException(status_code=400, detail="Instagram 2FA/Checkpoint required. Official app se login karein.")
        raise HTTPException(status_code=400, detail=f"Login Error: {err}")
