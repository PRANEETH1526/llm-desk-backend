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
    api_key: str | None = None  # Allow null
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

@app.post("/chat")
async def chat(request: ChatRequest):
    final_key = request.api_key
    # Aggressive check: If key is None, empty, or just spaces, kill it
    if final_key is None or final_key.strip() == "":
        final_key = os.getenv("GEMINI_API_KEY")

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

@app.post("/api/conversations/{conversation_id}/message/stream")
async def stream_message(conversation_id: str, request: StreamRequest):
    
    # 1. LOGGING: See exactly what the phone sent
    print(f"DEBUG: Chairman Model: {request.chairman.model}")
    
    # 2. KEY LOGIC: Clean the input
    api_key = request.chairman.api_key
    
    # If key is "None", "null" string, or empty, force fallback
    if api_key is None or api_key.strip() == "" or api_key.lower() == "null":
        print("DEBUG: Phone sent empty key. Switching to Server Key...")
        api_key = os.getenv("GEMINI_API_KEY")
        
        # Verify if Server Key exists
        if api_key:
            print(f"DEBUG: Server Key FOUND. Length: {len(api_key)}")
        else:
            print("DEBUG: CRITICAL - Server Key is MISSING from Render Environment!")

    # 3. STREAM GENERATOR
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
                 yield f"data: {json.dumps({'type': 'error', 'message': full_response})}\n\n"
                 return

            chunk_data = json.dumps({
                "role": "assistant",
                "content": full_response,
                "type": "content"
            })
            yield f"data: {chunk_data}\n\n"
            
        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")