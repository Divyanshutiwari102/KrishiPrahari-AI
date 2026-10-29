"""Shows which Gemini models your API key can use.  Run:  python list_models.py"""
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
key = os.getenv("GOOGLE_API_KEY")
if not key or key.startswith("your_"):
    raise SystemExit("Set a real GOOGLE_API_KEY in .env first.")

client = genai.Client(api_key=key)
print("Models that support generateContent (pick a 'flash' one, put it in .env as GEMINI_MODEL=...):\n")
for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    if "generateContent" in actions:
        print("  ", m.name.replace("models/", ""))