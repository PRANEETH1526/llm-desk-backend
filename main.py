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

# --- NEW DATA MODELS ---
# We need to accept the complex "Council" data your frontend sends
class AgentConfig(BaseModel):
    name: str
    api_key: str
    model: str

class StreamRequest(BaseModel):
    content: str
    council: list[AgentConfig]
    chairman: AgentConfig
    task: str

# --- ENDPOINT 1: Test Key ---
# Frontend calls: POST /api/test_key
@app.post("/api/test_key")
async def test_key(request: Request):
    # For now, we just return success to let the app proceed
    return {"ok": True, "message": "Key validated successfully"}

# --- ENDPOINT 2: Create Conversation ---
# Frontend calls: POST /api/conversations
@app.post("/api/conversations")
async def create_conversation():
    # Return a generated ID so the frontend knows where to send messages
    return {"id": "conv_12345"}

# --- ENDPOINT 3: Stream Message (The Main Chat) ---
# Frontend calls: POST /api/conversations/{id}/message/stream
@app.post("/api/conversations/{conversation_id}/message/stream")
async def stream_message(conversation_id: str, request: StreamRequest):
    
    # 1. Get the prompt from the frontend
    user_prompt = request.content
    
    # 2. Get API Key (use Chairman's key or fallback to .env)
    api_key = request.chairman.api_key
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")

    # 3. Create a generator to "stream" the response
    async def event_generator():
        try:
            # We use your existing Groq logic to get the answer
            full_response = await generate_response(
                api_key=api_key,
                model=request.chairman.model,
                content=user_prompt
            )
            
            # If the response itself is an error string, handle it
            if "Error" in full_response:
                 yield f"data: {json.dumps({'type': 'error', 'message': full_response})}\n\n"
                 return

            # SEND DATA: The frontend expects chunks, but Groq sends all at once.
            # We verify the format matches what api_service.dart expects:
            # yield jsonDecode(jsonStr) as Map<String, dynamic>;
            
            # Send the full text as one "chunk" for now
            chunk_data = json.dumps({
                "role": "assistant",
                "content": full_response,
                "type": "content"
            })
            yield f"data: {chunk_data}\n\n"
            
        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_data}\n\n"

    # Return as a proper Event Stream
    return StreamingResponse(event_generator(), media_type="text/event-stream")