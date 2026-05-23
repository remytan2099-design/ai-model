from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import secrets
import uvicorn
import httpx
import os
from dotenv import load_dotenv
from database import get_api_key_info, increment_requests, save_api_key, add_user, init_db

# Load API key from .env file (SECURE)
load_dotenv()

app = FastAPI(title="My AI API", description="My own API with my own keys")

# ============================================
# CORS - Allow your HTML page to call this API
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (for development)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)

# ============================================
# YOUR DEEPSEEK API KEY (Loaded from .env)
# ============================================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    print("⚠️ WARNING: DEEPSEEK_API_KEY not found in .env file")
    print("Create a .env file with: DEEPSEEK_API_KEY='sk_your_key_here'")
else:
    print(f"✅ DeepSeek API key loaded (starts with: {DEEPSEEK_API_KEY[:15]}...)")

# ============================================
# INITIALIZE DATABASE
# ============================================
init_db()

# ============================================
# REQUEST MODEL
# ============================================
class ChatRequest(BaseModel):
    prompt: str
    max_tokens: int = 500
    temperature: float = 0.7

# ============================================
# VALIDATE API KEY (Using Database)
# ============================================
def verify_api_key(x_api_key: str = Header(...)):
    """Check if the API key is valid using the database"""
    key_info = get_api_key_info(x_api_key)
    
    if not key_info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not key_info["is_active"]:
        raise HTTPException(status_code=401, detail="API key has been revoked")
    
    # Increment the request count
    increment_requests(x_api_key)
    
    return {
        "user_id": key_info["user_id"],
        "plan": key_info["plan"],
        "requests_used": key_info["requests_used"] + 1
    }

# ============================================
# GENERATE NEW API KEY (Admin only)
# ============================================
@app.get("/admin/generate-key")
def generate_new_key(user_id: str, username: str, plan: str = "basic"):
    """Generate a new API key and save to database"""
    
    # Add user to database
    add_user(user_id, username, plan)
    
    # Generate new API key
    new_key = f"sk_{secrets.token_urlsafe(32)}"
    
    # Save to database
    save_api_key(new_key, user_id, plan)
    
    return {
        "api_key": new_key,
        "user_id": user_id,
        "username": username,
        "plan": plan,
        "message": "Copy this key now. You won't see it again!"
    }

# ============================================
# CHAT ENDPOINT (Calls Real DeepSeek AI)
# ============================================
@app.post("/v1/chat")
async def chat(request: ChatRequest, user_info: dict = Depends(verify_api_key)):
    """Send a message to DeepSeek AI (requires your API key)"""
    
    if not DEEPSEEK_API_KEY:
        raise HTTPException(status_code=500, detail="DeepSeek API key not configured")
    
    # Call DeepSeek API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a helpful AI assistant."},
                    {"role": "user", "content": request.prompt}
                ],
                "max_tokens": request.max_tokens,
                "temperature": request.temperature
            },
            timeout=30.0
        )
    
    if response.status_code != 200:
        error_detail = response.text
        raise HTTPException(status_code=response.status_code, detail=f"DeepSeek API error: {error_detail}")
    
    result = response.json()
    ai_response = result["choices"][0]["message"]["content"]
    
    return {
        "success": True,
        "response": ai_response,
        "usage": {
            "user": user_info['user_id'],
            "plan": user_info['plan'],
            "requests_used": user_info['requests_used']
        }
    }

# ============================================
# HEALTH CHECK
# ============================================
@app.get("/health")
def health():
    """Check if the API is running"""
    from database import list_all_keys
    keys = list_all_keys()
    return {
        "status": "ok",
        "keys_active": len(keys),
        "deepseek_configured": bool(DEEPSEEK_API_KEY)
    }

# ============================================
# RUN THE SERVER
# ============================================
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║        YOUR AI API WITH DEEPSEEK IS RUNNING                 ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  Generate a key:  GET /admin/generate-key?user_id=test&username=test&plan=basic
    ║  Use the key:      POST /v1/chat -H "x-api-key: YOUR_KEY" -d '{"prompt":"Hello"}'
    ║  Check health:     GET /health
    ║  Server port:      8888
    ╚══════════════════════════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8888)