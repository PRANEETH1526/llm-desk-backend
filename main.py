
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from services.llm_service import generate_response

# 1. Load environment variables from the .env file
load_dotenv()

app = FastAPI()
# 2. CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (good for development)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Define Request Model
class ChatRequest(BaseModel):
    # Made optional (str | None) so we can fallback to .env if frontend sends null
    api_key: str | None = None  
    model: str
    content: str

@app.post("/chat")
async def chat(request: ChatRequest):
    # --- API KEY LOGIC ---
    # Priority: 1. Key sent from Frontend  2. Key in .env file
    final_api_key = request.api_key
    
    if not final_api_key:
        # If frontend didn't send a key, try loading the Groq key from .env
        final_api_key = os.getenv("GEMINI_API_KEY")
    
    # If we still don't have a key, stop here
    if not final_api_key:
        return {"error": "No API Key found. Please provide one in the request or set GROQ_API_KEY in .env"}

    # --- CALL SERVICE ---
    # No try/except block here so you can see real server errors in terminal if they happen
    result = await generate_response(
        api_key=final_api_key,
        model=request.model,
        content=request.content
    )
    
    # --- RESPONSE HANDLING ---
    # If the service returned an error string, send it back as a JSON error object
    if "Error" in result:
         return {"error": result}
         
    return {"response": result}