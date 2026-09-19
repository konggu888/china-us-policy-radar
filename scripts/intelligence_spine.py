#!/usr/bin/env python3
"""
Canonical intelligence spine for China-US Policy Radar.

Borrowed design ideas (not copied code):
- NewsSentry: separate source mention from canonical event, source health, lifecycle/history.
- osint-monitor: claim-level stance, corroboration, disagreement/conflict detection.
- GOIES: stable graph-like IDs and replayable snapshots.

This layer is deliberately deterministic and token-free. AI may enrich it later,
but the evidence registry must remain reproducible from public inputs.
"""
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NEWS = DATA / "news.json"
ARCHIVE = DATA / "archive"
OUT = DATA / "intelligence_spine.json"
HISTORY = DATA / "intelligence_spine_history.json"

STOP = set("的了和与及在对中美美国中国一个一种进行有关关于表示指出称将已是有被".split())

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def now():
    return datetime.now(timezone.utc)

def parse_dt(row):
    value = row.get("time") or row.get("updated") or row.get("published") or ""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None

def norm(text):
    text = re.sub(r"\s+", " ", str(text or "").lower()).strip()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)

def stable_id(prefix, value):
    return prefix + "-" + hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]

def source_meta(row):
    source = str(row.get("sourceOrg") or row.get("source") or "未知来源").strip()
    tier = str(row.get("sourceTier") or row.get("sourceType") or "").upper()
    official = bool(row.get("official")) or bool(re.search(
        r"gov|政府|国务院|外交部|商务部|财政部|央行|白宫|treasury|ustr|state department|federal reserve|eia|imf|world bank|un ",
        source, re.I))
    if official:
        tier = "PRIMARY"
    elif tier in {"官方", "OFFICIAL"}:
        tier = "PRIMARY"
    elif tier in {"国际机构", "INSTITUTION"}:
        tier = "INSTITUTION"
    elif tier in {"权威媒体", "MAJOR_MEDIA", "MEDIA"}:
        tier = "MEDIA"
    else:
        tier = "UNKNOWN"
    credibility = {"PRIMARY": .95, "INSTITUTION": .90, "MEDIA": .75, "UNKNOWN": .45}[tier]
    return source, tier, credibility

def stance(title):
    t = str(title or "")
    if re.search(r"否认|驳斥|反对|谴责|拒绝|警告|dispute|deny|reject|oppose|condemn|warn", t, re.I):
        return "DISAGREE"
    if re.search(r"支持|赞成|欢迎|同意|签署|达成|support|welcome|agree|sign|deal", t, re.I):
        return "AGREE"
    return "NEUTRAL"

def claim_text(row):
    title = row.get("titleZh") or row.get("title") or ""
    return str(title).strip()[:280]

def load_rows():
    rows = load_json(NEWS, [])
    if not isinstance(rows, list):
        rows = []
    if ARCHIVE.exists():
        for path in sorted(ARCHIVE.glob("*.json")):
            data = load_json(path, [])
            if isinstance(data, list):
                rows.extend(data)
    seen = set()
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("url") or row.get("id") or row.get("titleZh") or row.get("title") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out

def event_key(row):
    title = norm(row.get("titleZh") or row.get("title"))
    category = norm(row.get("ai_category") or row.get("cat") or "global")
    region = norm(row.get("ai_region") or row.get("region") or "global")
    # Title is the primary event fingerprint. Category/region prevent obvious
    # cross-domain collisions while still allowing multi-source corroboration.
    return "|".join((title, category, region))

def build():
    rows = load_rows()
    generated = now().isoformat()
    groups = defaultdict(list)
    source_stats = defaultdict(lambda: {"seen": 0, "recent": 0, "official": 0, "latest": None})
    cutoff = now() - timedelta(days=30)

    for row in rows:
        key = event_key(row)
        if key:
            groups[key].append(row)
        source, tier, _ = source_meta(row)
        stat = source_stats[source]
        stat["seen"] += 1
        if row.get("official") or tier == "PRIMARY":
            stat["official"] += 1
        dt = parse_dt(row)
        if dt and dt >= cutoff:
            stat["recent"] += 1
        if dt and (not stat["latest"] or dt > datetime.fromisoformat(stat["latest"])):
            stat["latest"] = dt.isoformat()

    events = []
    claims = []
    evidence = []
    conflicts = []

    for key, mentions in sorted(groups.items(), key=lambda kv: max(
        (parse_dt(x) or datetime.min.replace(tzinfo=timezone.utc) for x in kv[1]), default=datetime.min.replace(tzinfo=timezone.utc)
    ), reverse=True)[:500]:
        first = sorted(mentions, key=lambda x: parse_dt(x) or datetime.min.replace(tzinfo=timezone.utc))[0]
        title = claim_text(first)
        event_id = stable_id("evt", key)
        event_sources = set()
        claim_ids = []
        stance_counts = defaultdict(list)

        for row in mentions:
            source, tier, credibility = source_meta(row)
            source_id = stable_id("src", source.lower())
            evidence_id = stable_id("evd", str(row.get("url") or claim_text(row)))
            claim_id = stable_id("clm", event_id + "|" + claim_text(row))
            dt = parse_dt(row)
            age = (now() - dt).total_seconds() / 86400 if dt else None
            freshness = 1.0 if age is None or age <= 1 else .85 if age <= 7 else .55 if age <= 30 else .25
            weight = round(max(.05, min(1.0, credibility * freshness)), 3)
            st = stance(claim_text(row))
            event_sources.add(source)
            stance_counts[st].append(source)

            evidence.append({
                "id": evidence_id,
                "event_id": event_id,
                "claim_id": claim_id,
                "source_id": source_id,
                "source": source,
                "tier": tier,
                "url": row.get("url", ""),
                "published_at": row.get("time") or row.get("updated") or row.get("published") or "",
                "fetched_at": generated,
                "stance": st,
                "credibility": credibility,
                "freshness_factor": freshness,
                "evidence_weight": weight
            })
            if claim_id not in claim_ids:
                claim_ids.append(claim_id)
                claims.append({
                    "id": claim_id,
                    "event_id": event_id,
                    "text": claim_text(row),
                    "subject_region": row.get("ai_region") or row.get("region") or "global",
                    "category": row.get("ai_category") or row.get("cat") or "全球政策",
                    "stance": st,
                    "evidence_ids": [evidence_id]
                })
            else:
                for claim in claims:
                    if claim["id"] == claim_id:
                        claim["evidence_ids"].append(evidence_id)
                        break

        for st, sources in stance_counts.items():
            if st != "NEUTRAL" and sources:
                other = [s for k2, ss in stance_counts.items() if k2 not in {st, "NEUTRAL"} for s in ss]
                if other:
                    conflicts.append({
                        "event_id": event_id,
                        "type": "CLAIM_STANCE_CONFLICT",
                        "agree_sources": stance_counts.get("AGREE", []),
                        "disagree_sources": stance_counts.get("DISAGREE", []),
                        "note": "不同来源对同一事件标题呈现相反立场；需要人工/AI阅读全文核验，不能仅凭标题判定事实冲突。"
                    })
                    break

        status = "CORROBORATED" if len(event_sources) >= 2 else "SINGLE_SOURCE"
        events.append({
            "id": event_id,
            "canonical_key": key,
            "title": title,
            "category": first.get("ai_category") or first.get("cat") or "全球政策",
            "region": first.get("ai_region") or first.get("region") or "global",
            "status": status,
            "mention_count": len(mentions),
            "independent_source_count": len(event_sources),
            "source_ids": [stable_id("src", s.lower()) for s in sorted(event_sources)],
            "claim_ids": claim_ids,
            "first_seen": min((parse_dt(x) for x in mentions if parse_dt(x)), default=None).isoformat() if any(parse_dt(x) for x in mentions) else None,
            "last_seen": max((parse_dt(x) for x in mentions if parse_dt(x)), default=None).isoformat() if any(parse_dt(x) for x in mentions) else None
        })

    sources = []
    for name, stat in sorted(source_stats.items()):
        sources.append({
            "id": stable_id("src", name.lower()),
            "name": name,
            **stat,
            "health": "ACTIVE" if stat["recent"] > 0 else "STALE",
            "reliability_note": "来源层级是证据权重输入，不代表内容自动为真。"
        })

    # Replayable state history: preserve a compact per-run snapshot rather than overwriting prior state.
    previous = load_json(HISTORY, [])
    if not isinstance(previous, list):
        previous = []
    snapshot = {
        "run_at": generated,
        "event_count": len(events),
        "claim_count": len(claims),
        "evidence_count": len(evidence),
        "conflict_count": len(conflicts),
        "corroborated_event_count": sum(1 for e in events if e["status"] == "CORROBORATED"),
        "source_count": len(sources)
    }
    previous.append(snapshot)
    previous = previous[-168:]

    payload = {
        "schema_version": "1.0",
        "generated_at": generated,
        "method": "deterministic canonical-event/claim/evidence spine; AI enrichment optional",
        "inspiration": {
            "canonical_events": "NewsSentry",
            "claim_level_stance_and_conflicts": "osint-monitor",
            "graph_ids_and_replayable_snapshots": "GOIES"
        },
        "events": events[:300],
        "claims": claims[:1000],
        "evidence": evidence[:3000],
        "conflicts": conflicts[:300],
        "sources": sources[:500],
        "history": previous,
        "counters": snapshot
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    HISTORY.write_text(json.dumps(previous, ensure_ascii=False, indent=2), encoding="utf-8")
    print("intelligence spine:", json.dumps(snapshot, ensure_ascii=False))
    return payload

if __name__ == "__main__":
    build()
