import httpx
import json

async def generate_response(api_key: str, model: str, content: str):
    headers = {
        "Content-Type": "application/json"
    }
    
    # --- LOGIC 1: OPENROUTER (Key starts with sk-or) ---
    if api_key.startswith("sk-or"):
        # OpenRouter Endpoint
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        headers["HTTP-Referer"] = "https://llm-desk.com" 
        
        # OpenRouter Payload (OpenAI format)
        payload = {
            "model": model, 
            "messages": [{"role": "user", "content": content}]
        }
        provider = "OpenRouter"

    # --- LOGIC 2: GOOGLE GEMINI (Key starts with AIza) ---
    elif api_key.startswith("AIza"):
        # Google Endpoint
        # Map generic names to Google names if needed
        target_model = "gemini-1.5-flash"
        if "gemini" in model.lower(): target_model = model
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"
        
        # Google Payload (Gemini specific format)
        payload = {
            "contents": [{"parts": [{"text": content}]}]
        }
        provider = "Google"

    # --- LOGIC 3: GROQ (Key starts with gsk_) ---
    elif api_key.startswith("gsk_"):
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        
        payload = {
            "model": model, 
            "messages": [{"role": "user", "content": content}]
        }
        provider = "Groq"

    else:
        return f"Error: Unknown API Key format. Key starts with: {api_key[:5]}..."

    # --- EXECUTE REQUEST ---
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                return f"{provider} Error {response.status_code}: {response.text}"

            data = response.json()

            # --- PARSE RESPONSE ---
            if provider == "Google":
                try:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except:
                    return f"Google Parse Error: {data}"
            else:
                # OpenRouter and Groq share the same response format
                try:
                    return data["choices"][0]["message"]["content"]
                except:
                    return f"{provider} Parse Error: {data}"

        except Exception as e:
            return f"Connection Error to {provider}: {str(e)}"