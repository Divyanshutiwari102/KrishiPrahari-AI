"""
fix_upload_click.py  -  run ONCE from your project folder (where app.py is):   python fix_upload_click.py

Problem: the upload box only opened the file explorer when you clicked exactly on the purple text
"Click to upload or drag & drop" (a <label>).  Clicking the icon or the empty part of the dashed box
did nothing.  This makes the WHOLE box open the file explorer (no double-open when the text is clicked).
"""
import os, sys, shutil

OLD = "uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));\n"
NEW = OLD + (
    "// click anywhere inside the box (icon, hint, empty space) opens the file explorer\n"
    "uploadArea.addEventListener('click', (e) => {\n"
    "  if (e.target.closest('label, input, button, a')) return;   // label already opens it natively\n"
    "  imageUploader.click();\n"
    "});\n"
)
MARKER = "click anywhere inside the box (icon, hint, empty space)"

if not os.path.exists("script.js"):
    print("Run this inside the folder that contains script.js"); sys.exit(1)
with open("script.js", "r", encoding="utf-8") as f:
    t = f.read()
if MARKER in t:
    print("[OK]    script.js already has this fix")
elif t.count(OLD) != 1:
    print("[ERROR] script.js: expected line not found (file was changed). Send me the output of: findstr /n \"uploadArea.addEventListener\" script.js")
else:
    if not os.path.exists("script.js.bak"): shutil.copy("script.js", "script.js.bak")
    with open("script.js", "w", encoding="utf-8", newline="") as f:
        f.write(t.replace(OLD, NEW))
    print("[OK]    fixed script.js  -> restart app (python app.py) and hard-refresh (Ctrl+Shift+R)")
