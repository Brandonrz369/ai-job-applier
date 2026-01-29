import base64
import requests

OPENROUTER_KEY = None

def load_key():
    global OPENROUTER_KEY
    if not OPENROUTER_KEY:
        env = open('/root/job_bot/agent/.env').read()
        OPENROUTER_KEY = env.split('OPENROUTER_API_KEY=')[1].split('\n')[0].strip().strip('"')
    return OPENROUTER_KEY

def ask(screenshot_bytes, context, model):
    """Send screenshot to AI, get next action"""
    load_key()
    
    b64 = base64.b64encode(screenshot_bytes).decode()
    
    prompt = f"""{context}

What's the next action? Respond with ONLY one of:
CLICK x y
TYPE text
PRESS key
SCROLL up/down
DONE
FAILED reason"""

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
            json={
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            },
            timeout=60
        )
        
        data = resp.json()
        if 'choices' in data:
            return data['choices'][0]['message']['content'].strip()
        else:
            print(f"API error: {data}")
            return "FAILED API error"
    except Exception as e:
        print(f"Request error: {e}")
        return "FAILED request error"
