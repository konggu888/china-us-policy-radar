from pathlib import Path
p=Path("scenario.html")
s=p.read_text(encoding="utf-8")
needle="<script>\nconst esc="
inject="<script src="scripts/scenario_auth_supabase.js"></script>\n<script>\nconst esc="
if needle not in s:
    raise SystemExit("script insertion point missing")
s=s.replace(needle,inject,1)
p.write_text(s,encoding="utf-8")
