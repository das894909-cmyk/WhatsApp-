from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from instagrapi import Client

app = FastAPI()

# Database storage (Production ke liye yahan database connect hota hai)
DATABASE = {
    "accounts": [],
    "coins": 18627
}

class AccountModel(BaseModel):
    username: str
    session_id: str
    proxy_url: str = ""

class TaskModel(BaseModel):
    username: str
    target_user: str

# Frontend HTML UI
@app.get("/", response_class=HTMLResponse)
def home_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Insta Automation Panel</title>
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    </head>
    <body class="bg-blue-600 min-h-screen text-white">
        <div class="flex justify-between items-center p-4 bg-blue-700 shadow-md">
            <span class="font-bold text-lg">🚀 Insta Panel</span>
            <div class="bg-yellow-400 text-black px-3 py-1 rounded-full font-bold text-sm shadow">
                🟡 18627
            </div>
        </div>

        <div class="p-4 max-w-md mx-auto space-y-4">
            <div class="bg-white text-gray-800 p-4 rounded-xl shadow-lg">
                <h3 class="font-bold text-lg mb-3 text-blue-600">Link Instagram Account</h3>
                <input type="text" id="username" placeholder="Instagram Username" class="w-full p-2 border rounded-lg mb-2 text-sm">
                <input type="text" id="sessionId" placeholder="Session ID (sessionid cookie)" class="w-full p-2 border rounded-lg mb-2 text-sm">
                <input type="text" id="proxyUrl" placeholder="Proxy URL (optional: http://ip:port)" class="w-full p-2 border rounded-lg mb-3 text-sm">
                <button onclick="addAccount()" class="w-full bg-blue-600 text-white py-2 rounded-lg font-bold text-sm hover:bg-blue-700">
                    Connect Account
                </button>
            </div>

            <div class="bg-white text-gray-800 p-4 rounded-xl shadow-lg">
                <h3 class="font-bold text-lg mb-2 text-blue-600">Run Auto-Follow Task</h3>
                <input type="text" id="targetUser" placeholder="Target Username to Follow" class="w-full p-2 border rounded-lg mb-3 text-sm">
                <button onclick="startTask()" class="w-full bg-green-600 text-white py-2.5 rounded-lg font-bold hover:bg-green-700">
                    Start Automation (+4 Coins)
                </button>
                <p id="statusMsg" class="text-xs mt-2 text-center font-semibold text-gray-600"></p>
            </div>
        </div>

        <script>
            async function addAccount() {
                const username = document.getElementById('username').value;
                const sessionId = document.getElementById('sessionId').value;
                const proxyUrl = document.getElementById('proxyUrl').value;

                const response = await fetch('/api/add-account', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, session_id: sessionId, proxy_url: proxyUrl })
                });
                const result = await response.json();
                alert(result.message || result.detail);
            }

            async function startTask() {
                const username = document.getElementById('username').value;
                const targetUser = document.getElementById('targetUser').value;
                const msg = document.getElementById('statusMsg');

                msg.innerText = "Running automation in background...";
                const response = await fetch('/api/run-task', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, target_user: targetUser })
                });
                const result = await response.json();
                msg.innerText = result.message || result.detail;
            }
        </script>
    </body>
    </html>
    """

@app.post("/api/add-account")
def add_account(acc: AccountModel):
    DATABASE["accounts"].append(acc.dict())
    return {"status": "success", "message": f"Account {acc.username} connected successfully!"}

@app.post("/api/run-task")
def run_task(task: TaskModel):
    account = next((acc for acc in DATABASE["accounts"] if acc["username"] == task.username), None)
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found! Please connect first.")

    client = Client()
    
    if account["proxy_url"]:
        client.set_proxy(account["proxy_url"])

    try:
        client.login_by_sessionid(account["session_id"])
        target_id = client.user_id_from_username(task.target_user)
        client.user_follow(target_id)
        DATABASE["coins"] += 4
        
        return {"status": "success", "message": f"Successfully followed @{task.target_user} (+4 Coins Added)!"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Automation Failed: {str(e)}")