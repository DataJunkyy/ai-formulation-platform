from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from anthropic import Anthropic
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import init_db, get_db, Formulation

load_dotenv()

app = FastAPI(title="AI Formulation Platform")

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

@app.on_event("startup")
def startup_event():
    init_db()

class ChatRequest(BaseModel):
    message: str

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
        .formulation-item strong { color: #0066cc; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 AI Formulation Platform</h1>
        <p>Describe your product and let AI create a professional formulation.</p>
        
        <textarea id="message" placeholder="Example: Create a vitamin C serum for sensitive skin with a budget of $8 per unit"></textarea>
        
        <button onclick="createFormulation()">Create Formulation</button>
        
        <div id="response"></div>
        
        <div class="history">
            <h2>📚 Saved Formulations</h2>
            <button onclick="loadHistory()" style="margin-bottom: 15px;">Refresh History</button>
            <div id="history"></div>
        </div>
    </div>
    
    <script>
        window.onload = function() {
            loadHistory();
        };
        
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
                    headers: { 'Content-Type': 'application/json' },
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
                const response = await fetch('/formulations');
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

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
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
            formulation=response_text
        )
        db.add(db_formulation)
        db.commit()
        db.refresh(db_formulation)
        
        return {"response": response_text}
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/formulations")
async def get_formulations(db: Session = Depends(get_db)):
    formulations = db.query(Formulation).order_by(Formulation.created_at.desc()).limit(10).all()
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
