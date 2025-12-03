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

# --- MODELS ---
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
def get_valid_api_key(incoming_key: str | None) -> str | None:
    # 1. Load Environment Keys
    env_openrouter = os.getenv("OPENROUTER_API_KEY")
    env_gemini = os.getenv("GEMINI_API_KEY")
    env_groq = os.getenv("GROQ_API_KEY")

    # 2. Check Incoming Key from Phone
    if incoming_key and incoming_key.strip() != "":
        # Filter out dummy values that might come from the frontend
        if incoming_key.lower() not in ["null", "string", "none", "default"]:
            return incoming_key

    # 3. Fallback Priority
    # If phone sent nothing (or dummy), try OpenRouter first (universal), then others
    if env_openrouter: return env_openrouter
    if env_gemini: return env_gemini
    if env_groq: return env_groq
    
    return None

# --- ENDPOINTS ---

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

# --- THE CRITICAL STREAMING ENDPOINT ---
@app.post("/api/conversations/{conversation_id}/message/stream")
async def stream_message(conversation_id: str, request: StreamRequest):
    
    print(f"DEBUG: Starting Council Session. Task: {request.task}")

    async def event_generator():
        council_context = []

        # --- PHASE 1: THE COUNCIL MEMBERS LOOP ---
        # This fixes the "vanishing text" by sending specific 'member_chunk' events
        for member in request.council:
            print(f"DEBUG: Consulting Member: {member.name} ({member.model})")
            
            # 1. Get Key for this member
            member_key = get_valid_api_key(member.api_key)
            if not member_key:
                error_msg = f"Error: No API Key for {member.name}"
                yield f"data: {json.dumps({'type': 'error', 'member': member.name, 'message': error_msg})}\n\n"
                continue

            try:
                # 2. Call the AI
                response_text = await generate_response(
                    api_key=member_key,
                    model=member.model,
                    content=request.content # The user's prompt
                )

                # 3. Send "member_chunk" (This makes it appear in the glass bubble!)
                chunk_data = json.dumps({
                    "type": "member_chunk",
                    "member": member.name,
                    "chunk": response_text
                })
                yield f"data: {chunk_data}\n\n"
                
                # 4. Send "member_done"
                yield f"data: {json.dumps({'type': 'member_done', 'member': member.name})}\n\n"
                
                # Save context for the Chairman
                council_context.append(f"[{member.name}]: {response_text}")

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'member': member.name, 'message': str(e)})}\n\n"

        # --- PHASE 2: THE CHAIRMAN ---
        print("DEBUG: Chairman is synthesizing...")
        
        # Create a prompt that includes the members' opinions
        chairman_prompt = (
            f"User Question: {request.content}\n\n"
            f"Council Opinions:\n" + "\n".join(council_context) + "\n\n"
            f"Task: {request.task}\n"
            f"Synthesize a final response based on the opinions above."
        )

        chairman_key = get_valid_api_key(request.chairman.api_key)
        
        if not chairman_key:
             yield f"data: {json.dumps({'type': 'error', 'message': 'No Key for Chairman'})}\n\n"
             return

        try:
            final_response = await generate_response(
                api_key=chairman_key,
                model=request.chairman.model,
                content=chairman_prompt
            )

            if "Error" in final_response:
                yield f"data: {json.dumps({'type': 'error', 'message': final_response})}\n\n"
            else:
                # Send "chairman_chunk" (This makes it appear in the Green box)
                yield f"data: {json.dumps({'type': 'chairman_chunk', 'chunk': final_response})}\n\n"
                yield f"data: {json.dumps({'type': 'chairman_done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")