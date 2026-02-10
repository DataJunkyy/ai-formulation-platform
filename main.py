from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from anthropic import Anthropic
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import init_db, get_db, Formulation, User
from auth import get_password_hash, verify_password, create_access_token, get_current_user

load_dotenv()

app = FastAPI(title="AI Formulation Platform")

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

@app.on_event("startup")
def startup_event():
    init_db()

class ChatRequest(BaseModel):
    message: str

class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!DOCTYPE html>
<html>
<head>
    <title>AI Formulation Platform</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { color: #333; }
        .auth-section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 5px;
        }
        input {
            width: 100%;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        textarea {
            width: 100%;
            height: 100px;
            margin: 10px 0;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        button {
            background: #0066cc;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin-right: 10px;
        }
        button:hover { background: #0052a3; }
        #response {
            margin-top: 20px;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 5px;
            white-space: pre-wrap;
            display: none;
        }
        .loading { color: #666; font-style: italic; }
        .history {
            margin-top: 30px;
            padding: 20px;
            background: #f0f0f0;
            border-radius: 5px;
        }
        .history h2 { margin-top: 0; }
        .formulation-item {
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid #0066cc;
        }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 AI Formulation Platform</h1>
        
        <div id="authSection" class="auth-section">
            <h2>Login or Register</h2>
            <input type="email" id="email" placeholder="Email">
            <input type="password" id="password" placeholder="Password">
            <button onclick="register()">Register</button>
            <button onclick="login()">Login</button>
            <p id="authMessage"></p>
        </div>
        
        <div id="appSection" class="hidden">
            <p>Logged in as: <span id="userEmail"></span> <button onclick="logout()">Logout</button></p>
            <p>Describe your product and let AI create a professional formulation.</p>
            
            <textarea id="message" placeholder="Example: Create a vitamin C serum for sensitive skin with a budget of $8 per unit"></textarea>
            
            <button onclick="createFormulation()">Create Formulation</button>
            
            <div id="response"></div>
            
            <div class="history">
                <h2>📚 Your Formulations</h2>
                <button onclick="loadHistory()">Refresh History</button>
                <div id="history"></div>
            </div>
        </div>
    </div>
    
    <script>
        let token = localStorage.getItem('token');
        let userEmail = localStorage.getItem('email');
        
        if (token) {
            showApp();
        }
        
        function showApp() {
            document.getElementById('authSection').classList.add('hidden');
            document.getElementById('appSection').classList.remove('hidden');
            document.getElementById('userEmail').textContent = userEmail;
            loadHistory();
        }
        
        function showAuth() {
            document.getElementById('authSection').classList.remove('hidden');
            document.getElementById('appSection').classList.add('hidden');
        }
        
        async function register() {
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    document.getElementById('authMessage').textContent = 'Registered! Please login.';
                } else {
                    document.getElementById('authMessage').textContent = data.detail || 'Registration failed';
                }
            } catch (error) {
                document.getElementById('authMessage').textContent = 'Error: ' + error.message;
            }
        }
        
        async function login() {
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            const formData = new FormData();
            formData.append('username', email);
            formData.append('password', password);
            
            try {
                const response = await fetch('/token', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    token = data.access_token;
                    userEmail = email;
                    localStorage.setItem('token', token);
                    localStorage.setItem('email', email);
                    showApp();
                } else {
                    document.getElementById('authMessage').textContent = data.detail || 'Login failed';
                }
            } catch (error) {
                document.getElementById('authMessage').textContent = 'Error: ' + error.message;
            }
        }
        
        function logout() {
            localStorage.removeItem('token');
            localStorage.removeItem('email');
            token = null;
            showAuth();
        }
        
        async function createFormulation() {
            const message = document.getElementById('message').value;
            const responseDiv = document.getElementById('response');
            
            if (!message.trim()) {
                alert('Please describe your product first!');
                return;
            }
            
            responseDiv.style.display = 'block';
            responseDiv.innerHTML = '<div class="loading">Creating your formulation... (this takes 10-30 seconds)</div>';
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    responseDiv.innerHTML = '<strong>Error:</strong> ' + data.error;
                } else {
                    responseDiv.innerHTML = '<strong>Your Formulation:</strong><br><br>' + data.response;
                    loadHistory();
                }
            } catch (error) {
                responseDiv.innerHTML = '<strong>Error:</strong> ' + error.message;
            }
        }
        
        async function loadHistory() {
            const historyDiv = document.getElementById('history');
            historyDiv.innerHTML = '<div class="loading">Loading...</div>';
            
            try {
                const response = await fetch('/formulations', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                const data = await response.json();
                
                if (data.formulations && data.formulations.length > 0) {
                    historyDiv.innerHTML = data.formulations.map(f => 
                        '<div class="formulation-item"><strong>Request:</strong> ' + f.request + '<br><small>Created: ' + new Date(f.created_at).toLocaleString() + '</small></div>'
                    ).join('');
                } else {
                    historyDiv.innerHTML = '<p>No formulations yet. Create your first one above!</p>';
                }
            } catch (error) {
                historyDiv.innerHTML = '<strong>Error loading history:</strong> ' + error.message;
            }
        }
    </script>
</body>
</html>"""

@app.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/chat")
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": f"""You are an expert cosmetic chemist. Create a professional cosmetic formulation based on this request:

{request.message}

Provide a complete formulation including:
1. Product name and description
2. Complete ingredient list with INCI names and percentages
3. Manufacturing instructions (step-by-step)
4. Estimated cost per unit
5. Stability notes
6. Regulatory compliance notes

Format your response clearly and professionally."""
            }]
        )
        
        response_text = message.content[0].text
        
        db_formulation = Formulation(
            request=request.message,
            formulation=response_text,
            user_id=current_user.id
        )
        db.add(db_formulation)
        db.commit()
        db.refresh(db_formulation)
        
        return {"response": response_text}
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/formulations")
async def get_formulations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    formulations = db.query(Formulation).filter(Formulation.user_id == current_user.id).order_by(Formulation.created_at.desc()).limit(10).all()
    return {
        "formulations": [{
            "id": f.id,
            "request": f.request,
            "formulation": f.formulation,
            "created_at": f.created_at.isoformat()
        } for f in formulations],
        "count": len(formulations)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
