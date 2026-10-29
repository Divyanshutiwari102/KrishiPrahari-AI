"""
apply_fixes.py  -  run ONCE from inside your project folder (where app.py is):

    python apply_fixes.py

What it fixes (each file is backed up as <file>.bak first):
  1. google-generativeai (deprecated, FutureWarning)  ->  google-genai (new SDK)
  2. Gemini model name is read from .env (GEMINI_MODEL) instead of being hard-coded
  3. HuggingFaceEmbeddings deprecation warning  ->  langchain-huggingface
  4. Placeholder values from .env.example (MONGO_URI / GOOGLE_API_KEY) are treated as "not set"
     (removes the confusing 'DNS query name does not exist' MongoDB error)
  5. Terminal noise: TensorFlow oneDNN lines, HuggingFace symlink warning, httpx/HF request logs
  6. Flask: no double model-loading (reloader off) and listens on 127.0.0.1 only
  7. Old 'Gemini 1.5' comments, and the API-key prefix printed in logs, removed
"""
import os, sys, shutil

DEFAULT_MODEL = "gemini-3.5-flash"   # check with:  python list_models.py

def patch(path, edits):
    if not os.path.exists(path):
        print(f"[SKIP] {path} not found"); return False
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    original = text
    for old, new, count in edits:
        found = text.count(old)
        if found == 0:
            if new in text:
                print(f"   (already applied) {old.strip().splitlines()[0][:60]}")
                continue
            print(f"[ERROR] {path}: could not find expected text:\n   {old.strip().splitlines()[0][:80]}")
            print("        File was changed from the original; nothing written for this file.")
            return False
        if found != count:
            print(f"[ERROR] {path}: expected {count} match(es) but found {found} for:\n   {old.strip().splitlines()[0][:80]}")
            return False
        text = text.replace(old, new)
    if text != original:
        if not os.path.exists(path + ".bak"):
            shutil.copy(path, path + ".bak")
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"[OK]   patched {path}  (backup: {path}.bak)")
    else:
        print(f"[OK]   {path} already up to date")
    return True

# ───────────────────────── app.py ─────────────────────────
app_edits = [
    ("import os\nimport json\nimport time\n",
     'import os\n'
     'os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")          # hide oneDNN info lines\n'
     'os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")           # hide TensorFlow info/warnings\n'
     'os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")  # hide Windows symlink warning\n'
     'import json\nimport time\n', 1),
    ("  - Uses google-generativeai SDK (pip install google-generativeai) with gemini-1.5-flash",
     "  - Uses google-genai SDK (pip install google-genai); model name set by GEMINI_MODEL in .env", 1),
    ("# Google Generative AI SDK  (pip install google-generativeai)",
     "# Google Gen AI SDK  (pip install google-genai)", 1),
    ("import google.generativeai as genai",
     "from google import genai\nfrom google.genai import types as genai_types", 1),
    ("logger = logging.getLogger(__name__)\n",
     'logger = logging.getLogger(__name__)\n'
     '# Keep the terminal readable: hide per-request INFO logs of these libraries\n'
     'for _noisy in ("httpx", "httpcore", "huggingface_hub", "sentence_transformers", "urllib3"):\n'
     '    logging.getLogger(_noisy).setLevel(logging.WARNING)\n', 1),
    ('GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")\nif not GOOGLE_API_KEY:',
     'GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")\n'
     'if GOOGLE_API_KEY and GOOGLE_API_KEY.startswith("your_"):\n'
     '    GOOGLE_API_KEY = None   # placeholder from .env.example -> treat as not set\n'
     'if not GOOGLE_API_KEY:', 1),
    ('GEMINI_MODEL = "gemini-2.5-flash"   # gemini-1.5-flash deprecated; gemini-2.5-flash confirmed working',
     f'GEMINI_MODEL = os.getenv("GEMINI_MODEL", "{DEFAULT_MODEL}")   # change in .env if Google retires it', 1),
    ("if GOOGLE_API_KEY:\n    genai.configure(api_key=GOOGLE_API_KEY)\n",
     "gemini_client = None\nif GOOGLE_API_KEY:\n    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)\n", 1),
    ("Uses google-generativeai SDK (genai.GenerativeModel).",
     "Uses google-genai SDK (genai.Client).", 1),
    ("Gemini 1.5 Flash", "Gemini", 3),
    ('    if not GOOGLE_API_KEY:\n        raise RuntimeError("Gemini SDK not configured (no API key).")\n\n'
     '    model_instance = genai.GenerativeModel(\n'
     '        model_name=GEMINI_MODEL,\n'
     '        system_instruction=system_instruction,\n'
     '        generation_config=genai.types.GenerationConfig(\n'
     '            max_output_tokens=1024,\n'
     '            temperature=0.7,\n'
     '        ),\n'
     '    )\n',
     '    if not gemini_client:\n        raise RuntimeError("Gemini SDK not configured (no API key).")\n\n'
     '    chat_config = genai_types.GenerateContentConfig(\n'
     '        system_instruction=system_instruction,\n'
     '        max_output_tokens=1024,\n'
     '        temperature=0.7,\n'
     '    )\n'
     '    # Convert stored history ({"role", "parts": [text, ...]}) into SDK Content objects\n'
     '    sdk_history = [\n'
     '        genai_types.Content(\n'
     '            role=m["role"],\n'
     '            parts=[genai_types.Part(text=t) for t in m["parts"]],\n'
     '        )\n'
     '        for m in history\n'
     '    ]\n', 1),
    ('            chat = model_instance.start_chat(history=history)\n',
     '            chat = gemini_client.chats.create(\n'
     '                model=GEMINI_MODEL, config=chat_config, history=sdk_history\n'
     '            )\n', 1),
    ('                {"role": m.role, "parts": [p.text for p in m.parts]}\n                for m in chat.history\n',
     '                {"role": m.role, "parts": [p.text for p in m.parts if p.text]}\n                for m in chat.get_history()\n', 1),
    ('    app.run(\n        host="0.0.0.0",\n        port=5000,\n        debug=True\n    )',
     '    # debug=False -> model/RAG load only once (faster start); 127.0.0.1 -> not exposed on the network\n'
     '    app.run(host="127.0.0.1", port=5000, debug=False)', 1),
]

# ──────────────────── services/rag_service.py ────────────────────
rag_edits = [
    ("# Working Gemini model (confirmed via API probe — gemini-1.5-flash was deprecated)\nGEMINI_MODEL = \"gemini-2.5-flash\"",
     "from dotenv import load_dotenv\nload_dotenv()\n\n"
     "# Gemini model name comes from .env (GEMINI_MODEL); change it there if Google retires a model\n"
     f"GEMINI_MODEL = os.getenv(\"GEMINI_MODEL\", \"{DEFAULT_MODEL}\")", 1),
    ("            from langchain_community.embeddings import HuggingFaceEmbeddings\n            self._embeddings",
     "            try:\n                from langchain_huggingface import HuggingFaceEmbeddings\n"
     "            except ImportError:\n                from langchain_community.embeddings import HuggingFaceEmbeddings\n"
     "            self._embeddings", 1),
    ("        Call Gemini (model: gemini-2.5-flash) with retry on quota/server errors.\n"
     "        gemini-1.5-flash was deprecated and removed from the API in 2025.\n",
     "        Call Gemini (model set by GEMINI_MODEL in .env) with retry on quota/server errors.\n", 1),
    ("            import google.generativeai as genai\n        except ImportError:\n"
     "            return \"Gemini SDK not installed. Run: pip install google-generativeai\"",
     "            from google import genai\n            from google.genai import types as genai_types\n        except ImportError:\n"
     "            return \"Gemini SDK not installed. Run: pip install google-genai\"", 1),
    ('        api_key = os.getenv("GOOGLE_API_KEY")\n        if not api_key:',
     '        api_key = os.getenv("GOOGLE_API_KEY")\n'
     '        if api_key and api_key.startswith("your_"):\n            api_key = None   # placeholder from .env.example\n'
     '        if not api_key:', 1),
    (r'f"  API key detected : True ({api_key[:8]}...)\n"',
     r'f"  API key detected : True\n"', 1),
    ("        genai.configure(api_key=api_key)\n"
     "        model = genai.GenerativeModel(\n"
     "            model_name=GEMINI_MODEL,   # ← was 'gemini-1.5-flash' (DEAD)\n"
     "            system_instruction=system_prompt,\n"
     "            generation_config=genai.types.GenerationConfig(\n"
     "                max_output_tokens=1024,\n"
     "                temperature=0.3,   # Lower temp for factual RAG answers\n"
     "            ),\n"
     "        )\n",
     "        client = genai.Client(api_key=api_key)\n"
     "        gen_config = genai_types.GenerateContentConfig(\n"
     "            system_instruction=system_prompt,\n"
     "            max_output_tokens=1024,\n"
     "            temperature=0.3,   # Lower temp for factual RAG answers\n"
     "        )\n", 1),
    ("                response = model.generate_content(user_message)\n",
     "                response = client.models.generate_content(\n"
     "                    model=GEMINI_MODEL, contents=user_message, config=gen_config\n"
     "                )\n", 1),
]

# ───────────────────────── ingest.py ─────────────────────────
ingest_edits = [
    ("        from langchain_community.embeddings import HuggingFaceEmbeddings\n    except ImportError:",
     "        try:\n            from langchain_huggingface import HuggingFaceEmbeddings\n"
     "        except ImportError:\n            from langchain_community.embeddings import HuggingFaceEmbeddings\n"
     "    except ImportError:", 1),
]

# ───────────────────────── database.py ─────────────────────────
db_edits = [
    ('MONGO_URI             = os.getenv("MONGO_URI")\n',
     'MONGO_URI             = os.getenv("MONGO_URI")\n'
     'if MONGO_URI and ("username:password@" in MONGO_URI or "<" in MONGO_URI):\n'
     '    MONGO_URI = None   # placeholder from .env.example -> run in offline mode instead of failing\n', 1),
]

# ───────────────────────── requirements.txt ─────────────────────────
req_edits = [
    ("google-generativeai", "google-genai", 1),
    ("faiss-cpu\n", "faiss-cpu\nlangchain-huggingface\n", 1),
]

if __name__ == "__main__":
    if not os.path.exists("app.py"):
        print("Run this from the folder that contains app.py"); sys.exit(1)
    ok = True
    ok &= patch("app.py", app_edits)
    ok &= patch(os.path.join("services", "rag_service.py"), rag_edits)
    ok &= patch("ingest.py", ingest_edits)
    ok &= patch("database.py", db_edits)
    ok &= patch("requirements.txt", req_edits)
    print()
    if ok:
        print("All fixes applied. Next:")
        print("  pip install google-genai langchain-huggingface")
        print("  (optional) pip uninstall -y google-generativeai")
        print("  python list_models.py      # pick a working model, put it in .env as GEMINI_MODEL=...")
        print("  python app.py")
    else:
        print("Some files were NOT patched (see errors above). Send me that output.")