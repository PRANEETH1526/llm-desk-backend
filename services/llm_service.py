import httpx
import json

async def generate_response(api_key: str, model: str, content: str):
    # Default to Gemini 1.5 Flash if no model is specified or if an incompatible model name is sent
    # Valid Gemini models: "gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"
    target_model = "gemini-1.5-flash"
    
    if "gemini" in model.lower():
        target_model = model
    
    # Gemini uses the API Key in the URL, not the Headers
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"

    headers = {
        "Content-Type": "application/json"
    }

    # Gemini expects a different JSON structure than OpenAI/Groq
    payload = {
        "contents": [{
            "parts": [{"text": content}]
        }]
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                return f"Error {response.status_code}: {response.text}"

            data = response.json()
            
            # Parse Gemini's specific response structure
            # structure: candidates[0] -> content -> parts[0] -> text
            try:
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        return candidate["content"]["parts"][0]["text"]
                    else:
                        # Sometimes Gemini blocks content for safety
                        return "Response blocked by safety filters."
                else:
                    return f"API Error (No candidates): {data}"
            except KeyError:
                return f"Parsing Error: {data}"

        except Exception as e:
            return f"Connection Error: {str(e)}"