from pathlib import Path

p = Path("scenario.html")
s = p.read_text(encoding="utf-8")
script = '<script src="scripts/scenario_auth_supabase.js"></script>'

if script in s:
    print("Supabase auth script already present; no change needed.")
else:
    needle = "<script>\nconst esc="
    if needle not in s:
        raise SystemExit("script insertion point missing")
    s = s.replace(needle, script + "\n<script>\nconst esc=", 1)
    p.write_text(s, encoding="utf-8")
    print("Supabase auth script inserted.")
