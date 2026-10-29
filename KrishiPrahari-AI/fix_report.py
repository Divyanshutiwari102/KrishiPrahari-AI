"""
fix_report.py  -  run ONCE from your project folder (where app.py is):   python fix_report.py

Fixes found by reading your generated PDF report:
  1. "Plant Type: Early"  -> real plant (Tomato). Frontend now derives it from the model class name.
  2. "KrishiPrahari AI AI Engine"  -> "KrishiPrahari AI Engine"  (double AI after the rename)
  3. Treatment list numbered 1. 2. 3. under three different headings -> numbers stripped
  4. "Persisted in MongoDB Atlas" / "Atlas Sync Status" -> you use local MongoDB, text made accurate
  5. "agroai.scans" shown in the report -> "scans" (old brand name no longer visible)
  6. "DIGITALLY VERIFIED REPORT" -> "REPORT RECORD" (nothing is digitally signed)
  7. Time was local time labelled "UTC" -> label removed
  8. Smart insights: made-up-looking numbers relabelled "Indicative ...", and the
     "AI Recommendation Score" (= confidence x 0.6, so a MORE certain diagnosis scored LOWER) removed
Backups: <file>.bak (kept from the first run if it already exists).  Nothing is written if text does not match.
"""
import os, sys, shutil

def read(p):
    with open(p, "r", encoding="utf-8") as f: return f.read()

def patch(path, edits):
    if not os.path.exists(path):
        print(f"[SKIP]  {path} not found"); return True
    text = read(path); orig = text
    for edit in edits:
        old, new, count = edit[:3]
        marker = edit[3] if len(edit) > 3 else None
        if marker and marker in text: continue          # already applied
        n = text.count(old)
        if n == 0 and new in text: continue
        if n != count:
            print(f"[ERROR] {path}: expected {count}, found {n} for: {old.strip()[:70]!r}"); return False
        text = text.replace(old, new)
    if text != orig:
        if not os.path.exists(path + ".bak"): shutil.copy(path, path + ".bak")
        with open(path, "w", encoding="utf-8", newline="") as f: f.write(text)
        print(f"[OK]    fixed {path}")
    else:
        print(f"[OK]    {path} already up to date")
    return True

pdf_edits = [
    ("AI AI Engine", "AI Engine", 2),
    ('''                b = b[len(prefix):]
                break
        if b:
            bullets.append(b)''',
     '''                b = b[len(prefix):]
                break
        import re as _re
        b = _re.sub(r"^\\d+[.)]\\s*", "", b)      # drop "1. " / "2) " numbering
        if b:
            bullets.append(b)''', 2),
    ('"Persisted in MongoDB Atlas"', '"Persisted in MongoDB"', 1),
    ('["Atlas Sync Status",      sync_status],', '["Sync Status",            sync_status],', 1),
    ('["Database Name",          "agroai.scans"],', '["Collection",             "scans"],', 1),
    ('"DIGITALLY VERIFIED REPORT"', '"REPORT RECORD"', 1),
    ('SectionHeader("VERIFICATION & DIGITAL RECORD"', 'SectionHeader("REPORT ID & QR RECORD"', 1),
    ('"%Y-%m-%d %H:%M:%S UTC"', '"%Y-%m-%d %H:%M:%S"', 1),
    ('("Estimated Crop Damage Risk",      damage_risk),', '("Indicative Crop Damage Risk",     damage_risk),', 1),
    ('("Recovery Probability",            recovery_prob),', '("Indicative Recovery Rate",        recovery_prob),', 1),
    ('''        ("AI Recommendation Score",         f"{rec_score}/100 — {'Actionable' if rec_score >= 70 else 'Advisory'}"),\n''', '', 1),
]
js_edits = [
    ("    imageDataUrl,\n    disease:      data.disease_name,\n",
     "    imageDataUrl,\n    disease:      data.disease_name,\n"
     "    plantType:    (data.prediction || '').split('___')[0].replace(/_/g, ' ').trim(),\n", 1,
     "plantType:    (data.prediction"),
    ('plant_type:      disease.split(" ")[0] || "Plant",',
     'plant_type:      lastResult?.plantType || disease.split(" ")[0] || "Plant",', 1),
]

if __name__ == "__main__":
    if not os.path.exists("app.py"):
        print("Run this inside the folder that contains app.py"); sys.exit(1)
    ok = patch("pdf_generator.py", pdf_edits) & patch("script.js", js_edits)
    print()
    print("Done. Restart `python app.py`, hard-refresh (Ctrl+Shift+R), scan again and download a NEW report."
          if ok else "Some edits were skipped (see errors). Send me this output.")