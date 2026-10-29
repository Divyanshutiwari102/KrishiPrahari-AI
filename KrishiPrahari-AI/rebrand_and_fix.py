"""
rebrand_and_fix.py  -  run ONCE from your project folder (where app.py is):

    python rebrand_and_fix.py "YourNewName"        e.g.  python rebrand_and_fix.py FasalSetu

1. Replaces the visible name "AgroAI" with your name everywhere (HTML, JS, JSON, PDF report,
   Python docstrings, knowledge-base text).  The logo "Agro<span>AI</span>" is split automatically:
   FasalSetu -> Fasal<span>Setu</span>,  "Crop Sentinel" -> Crop <span>Sentinel</span>.
   Lowercase internal ids (agroai_jwt, agroai_history, database name "agroai", 'agroai:auth')
   are left alone ON PURPOSE: renaming them would log users out and orphan your MongoDB data.
2. Fixes real bugs/claims found while testing:
   - chat bubbles: stray '*' and broken italics/bullets in the Expert Assistant (new safe renderer)
   - post-scan chat: bold text and bullet items rendered EMPTY ('<strong></strong>', missing $1)
   - "Gemini 1.5 Flash" badge (outdated)  ->  "Gemini AI"
   - "97.4%" / "97%+" accuracy  ->  96.6% / 96%+  (your training_hist.json says val_accuracy 0.9656)
   - hides the 'AFC is enabled' log line of the new Gemini SDK
Every changed file is backed up as <file>.bak first.  Nothing is changed if a file does not match.
"""
import os, re, sys, shutil

OLD = "AgroAI"
SKIP_DIRS = {"venv", ".git", "__pycache__", "vectorstore", ".idea", "node_modules", "test"}
SKIP_FILES = {"README.md", "apply_fixes.py", "rebrand_and_fix.py", "list_models.py", ".env"}
TEXT_EXT = {".html", ".js", ".css", ".json", ".py", ".txt"}
TEXT_NAMES = {".gitignore", ".env.example"}

def split_name(n):
    if " " in n:
        i = n.rfind(" ") + 1
    else:
        caps = [k for k, c in enumerate(n) if c.isupper() and k > 0]
        i = caps[-1] if caps else None
    return (n[:i], n[i:]) if i else (n, "")

def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

def write(p, text):
    if not os.path.exists(p + ".bak"):
        shutil.copy(p, p + ".bak")
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(text)

def patch(path, edits):
    if not os.path.exists(path):
        print(f"[SKIP]  {path} not found"); return True
    text = read(path); orig = text
    for old, new, count in edits:
        n = text.count(old)
        if n == 0 and new in text:
            continue                      # already applied
        if n != count:
            print(f"[ERROR] {path}: expected {count} match(es), found {n} for: {old.strip()[:70]!r}")
            return False
        text = text.replace(old, new)
    if text != orig:
        write(path, text); print(f"[OK]    fixed {path}")
    return True

NEW_RENDER = r"""  function _renderMarkdown(text) {
    // Safe, line-based renderer: escapes HTML first, then handles **bold**, *italic*, bullets, ---
    const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const inline = s => esc(s)
      .replace(/\*\*(\S(?:.*?\S)?)\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[\s(])\*(\S(?:.*?\S)?)\*(?=[\s).,;:!?]|$)/g, '$1<em>$2</em>');
    let out = '', inList = false;
    for (const raw of String(text).split(/\r?\n/)) {
      const m = raw.match(/^\s*[*\-•]\s+(.*)$/);
      if (m) {
        if (!inList) { out += '<ul>'; inList = true; }
        out += '<li>' + inline(m[1]) + '</li>';
        continue;
      }
      if (inList) { out += '</ul>'; inList = false; }
      if (raw.trim() === '') { out += '<br>'; continue; }
      if (/^\s*-{3,}\s*$/.test(raw)) { out += '<hr>'; continue; }
      out += inline(raw) + '<br>';
    }
    if (inList) out += '</ul>';
    return out;
  }
"""
OLD_RENDER = r"""  function _renderMarkdown(text) {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
      .replace(/\n{2,}/g, '<br><br>')
      .replace(/\n/g, '<br>');
  }
"""

def main():
    if len(sys.argv) < 2 or not os.path.exists("app.py"):
        print('Usage (inside the folder that has app.py):  python rebrand_and_fix.py "YourNewName"'); sys.exit(1)
    name = sys.argv[1].strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 \-]{2,23}", name):
        print("Name must be 3-24 characters: letters, digits, space or hyphen."); sys.exit(1)
    a, b = split_name(name)
    slug = re.sub(r"[^A-Za-z0-9]+", "", name)      # e.g. "KrishiPrahari AI" -> "KrishiPrahariAI"
    ok = True

    # ---- 1. rename ----------------------------------------------------------
    logo_old = 'Agro<span class="logo-accent">AI</span>'
    logo_new = f'{a}<span class="logo-accent">{b}</span>' if b else a
    changed = 0
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if fn in SKIP_FILES or fn.endswith(".bak"):
                continue
            if ext not in TEXT_EXT and fn not in TEXT_NAMES:
                continue
            p = os.path.join(root, fn)
            try:
                t = read(p)
            except Exception:
                continue
            # filenames (AgroAI_Report_x.pdf ...) get a space-free version of the name
            # window.AgroAI is a JavaScript identifier -> must also be space-free
            n = (t.replace(logo_old, logo_new)
                  .replace("window." + OLD, "window." + slug)
                  .replace(OLD + "_", slug + "_")
                  .replace(OLD, name))
            if n != t:
                write(p, n); changed += 1
    print(f"[OK]    renamed '{OLD}' -> '{name}' in {changed} files (logo: {logo_new})")

    # ---- 2. fixes -----------------------------------------------------------
    ok &= patch("script.js", [
        (OLD_RENDER, NEW_RENDER, 1),
        ("'<strong></strong>'", "'<strong>$1</strong>'", 1),
        ("'<em></em>'", "'<em>$1</em>'", 1),
        ("'<li></li>'", "'<li>$1</li>'", 1),
    ])
    ok &= patch("index.html", [
        ('<div class="fc-label">Model Accuracy</div><div class="fc-value">97.4%</div>',
         '<div class="fc-label">Validation Accuracy</div><div class="fc-value">96.6%</div>', 1),
        ("97%+ accuracy", "96%+ validation accuracy", 1),
        ('<div class="feature-tag">Gemini 1.5 Flash</div>', '<div class="feature-tag">Gemini AI</div>', 1),
    ])
    ok &= patch(os.path.join("translations", "en.json"), [("97%+ accuracy", "96%+ validation accuracy", 1)])
    ok &= patch(os.path.join("translations", "hi.json"), [("97%+ सटीकता", "96%+ सटीकता", 1)])
    ok &= patch("app.py", [
        ('("httpx", "httpcore", "huggingface_hub", "sentence_transformers", "urllib3")',
         '("httpx", "httpcore", "huggingface_hub", "sentence_transformers", "urllib3", "google_genai")', 1),
    ])

    print()
    if ok:
        print("Done. Now: hard-refresh the browser (Ctrl+Shift+R) after restarting `python app.py`.")
        print("Optional (cosmetic): the knowledge-base text was renamed too; `python ingest.py` would rebuild the")
        print("vectorstore with it, but the app works fine without rebuilding.")
        print("Still TODO by you: '1.8s' response time and '100% Offline Ready' on the home page are hard-coded")
        print("claims - measure/reword them (see my message).")
    else:
        print("Some edits were skipped (see errors). Send me the output.")

if __name__ == "__main__":
    main()