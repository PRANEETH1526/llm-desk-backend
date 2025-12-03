import httpx
import os

# CHANGED: Use Groq URL instead of OpenRouter
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

async def generate_response(api_key: str, model: str, content: str):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # CHANGED: Map generic model names to specific Groq model IDs
    # Groq supports: llama3-8b-8192, llama3-70b-8192, mixtral-8x7b-32768, gemma-7b-it
    target_model = model
    if "llama" in model.lower():
        target_model = "llama3-70b-8192" # Fallback to a valid Groq model
    elif "mixtral" in model.lower():
        target_model = "mixtral-8x7b-32768"
    else:
        # Default fallback if the frontend sends a model Groq doesn't know
        target_model = "llama3-70b-8192"

    payload = {
        "model": target_model,
        "messages": [
            {"role": "user", "content": content}
        ],
        "max_tokens": 300
    }

    # Verify we are sending to the right place
    print(f"DEBUG: Sending to {GROQ_URL} with model {target_model}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(GROQ_URL, json=payload, headers=headers)
            
            if response.status_code != 200:
                # Print exact error for debugging
                print(f"API ERROR: {response.text}") 
                return f"Error {response.status_code}: {response.text}"

            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                return f"API Error: {data}"
                
        except Exception as e:
            return f"Connection Error: {str(e)}"