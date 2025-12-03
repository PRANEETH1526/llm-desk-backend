import os
import json
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.llm_service import generate_response

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AgentConfig(BaseModel):
    name: str
    api_key: str | None = None
    model: str

class StreamRequest(BaseModel):
    content: str
    council: list[AgentConfig]
    chairman: AgentConfig
    task: str

class ChatRequest(BaseModel):
    api_key: str | None = None
    model: str
    content: str

# --- HELPER: Smart Key Selection ---
# --- HELPER: Smart Key Selection ---
def get_valid_api_key(incoming_key: str | None) -> str | None:
    # 1. Check incoming key from phone
    if incoming_key and incoming_key.strip() != "" and incoming_key.lower() not in ["null", "string", "none"]:
        return incoming_key

    # 2. Fallback: Try OpenRouter Key first (Most flexible)
    openrouter = os.getenv("OPENROUTER_API_KEY")
    if openrouter:
        return openrouter
        
    # 3. Fallback: Try Gemini Key
    gemini = os.getenv("GEMINI_API_KEY")
    if gemini:
        return gemini

    # 4. Fallback: Try Groq Key
    return os.getenv("GROQ_API_KEY")
@app.post("/chat")
async def chat(request: ChatRequest):
    final_key = get_valid_api_key(request.api_key)
    if not final_key:
        return {"error": "Critical: No API Key found in Request OR Environment variables."}

    result = await generate_response(
        api_key=final_key,
        model=request.model,
        content=request.content
    )
    if "Error" in result:
         return {"error": result}
    return {"response": result}

@app.post("/api/conversations")
async def create_conversation():
    return {"id": "conv_12345"}

@app.post("/api/test_key")
async def test_key(request: Request):
    return {"ok": True, "message": "Key validated successfully"}

@app.post("/api/conversations/{conversation_id}/message/stream")
async def stream_message(conversation_id: str, request: StreamRequest):
    print(f"DEBUG: Chairman Model requested: {request.chairman.model}")
    
    api_key = get_valid_api_key(request.chairman.api_key)
    
    if api_key:
        masked_key = api_key[:5] + "..." if len(api_key) > 5 else "SHORT_KEY"
        print(f"DEBUG: Using API Key starting with: {masked_key}")
    else:
        print("DEBUG: CRITICAL - Server Key is MISSING from Render Environment!")

    async def event_generator():
        if not api_key:
            error_msg = json.dumps({"type": "error", "message": "Server Config Error: No API Key available."})
            yield f"data: {error_msg}\n\n"
            return

        try:
            full_response = await generate_response(
                api_key=api_key,
                model=request.chairman.model,
                content=request.content
            )
            
            if "Error" in full_response:
                 print(f"DEBUG: Gemini API Error: {full_response}")
                 yield f"data: {json.dumps({'type': 'error', 'message': full_response})}\n\n"
                 return

            chunk_data = json.dumps({
                "role": "assistant",
                "content": full_response,
                "type": "content"
            })
            yield f"data: {chunk_data}\n\n"
            
        except Exception as e:
            print(f"DEBUG: Exception: {str(e)}")
            error_data = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")