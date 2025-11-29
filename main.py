from fastapi import FastAPI
from pydantic import BaseModel
from services.llm_service import generate_response
from fastapi.middleware.cors import CORSMiddleware  # <--- IMPORT THIS

app = FastAPI()

# <--- ADD THIS BLOCK
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# <--- END BLOCK

class ChatRequest(BaseModel):
    api_key: str
    model: str
    content: str

@app.post("/chat")
async def chat(request: ChatRequest):
    # No try/except block here so you can see the real error in the terminal
    result = await generate_response(
        api_key=request.api_key,
        model=request.model,
        content=request.content
    )
    
    # If the result contains "Error", return it cleanly
    if "Error" in result:
         return {"error": result}
         
    return {"response": result}