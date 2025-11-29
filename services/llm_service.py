import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

async def generate_response(api_key: str, model: str, content: str):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Ensure model name is correct for OpenRouter
    target_model = model
    if model == "meta-llama/llama-3.1-70b":
        target_model = "meta-llama/llama-3.1-70b-instruct"

    payload = {
        "model": target_model,
        "messages": [
            {"role": "user", "content": content}
        ],
        "max_tokens": 300
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
            
            # Check for non-200 status
            if response.status_code != 200:
                return f"Error {response.status_code}: {response.text}"

            data = response.json()
            
            # Check if choices exist
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                return f"API Error: {data}"
                
        except Exception as e:
            return f"Connection Error: {str(e)}"