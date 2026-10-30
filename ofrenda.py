#!/usr/bin/env python3
"""
Ofrenda Keeper — a local remembrance keeper for Dia de los Muertos.

You write memories of loved ones as simple .txt files in a folder.
One command weaves them into a beautiful, self-contained remembrance
page (out/ofrenda.html) that lives entirely on your machine.

Design (same honest architecture as our other local-AI tools):
- RULES do the structure: parsing memory files, HTML escaping, page layout.
- GEMMA (local, via Ollama) does only the writing: a short tribute per
  person, in a warm and respectful tone.
- If Ollama is unreachable, a clearly-labelled template fallback writes
  the tribute instead. Nothing is ever faked: every tribute is tagged
  with the engine that wrote it.

Privacy: memories/ and out/ are gitignored. Nothing is uploaded anywhere.
Your family's stories never leave this machine.
"""
import argparse
import html
import json
import re
import sys
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"

# ---------------------------------------------------------------- parsing

FIELD_RE = re.compile(r"^(name|dates|place|memory)\s*:\s*(.*)$", re.IGNORECASE)


def parse_memory_file(path: Path) -> dict:
    """Parse one memory file. Only the four known fields are read; the
    Memory field may span multiple lines. Missing optional fields become
    empty strings — never invented."""
    person = {"name": "", "dates": "", "place": "", "memory": "", "source": path.name}
    current = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        m = FIELD_RE.match(raw.strip())
        if m:
            current = m.group(1).lower()
            person[current] = m.group(2).strip()
        elif current == "memory" and raw.strip():
            person["memory"] += (" " if person["memory"] else "") + raw.strip()
        # unknown lines outside Memory are ignored on purpose
    if not person["name"]:
        person["name"] = path.stem.replace("_", " ").title()
    return person


# ------------------------------------------------------------------- gemma

def ask_gemma_tribute(model: str, person: dict) -> str | None:
    """Ask the local model for a 2-3 sentence tribute. Bracketed words are
    instructions, never to be copied into the answer (small models echo
    schema examples otherwise)."""
    prompt = (
        "You write short remembrances for a family's Dia de los Muertos ofrenda. "
        "Write a warm, respectful tribute of 2-3 sentences for the person described "
        "below. The words inside < > are instructions for you — never copy them "
        "into your answer. Reply with ONLY the tribute text, no quotes, no preamble.\n\n"
        f"Name: <the person's name: {person['name']}>\n"
        f"Dates: <their dates: {person['dates'] or 'not given'}>\n"
        f"Place: <their place: {person['place'] or 'not given'}>\n"
        f"A memory of them: <{person['memory'] or 'no memory written yet'}>"
    )
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read())["response"].strip()
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError):
        return None


def clean_tribute(text: str | None, person: dict) -> str | None:
    """Echo guard: if the model returned instructions, placeholders or an
    empty string instead of a real tribute, reject it so the honest
    template fallback is used instead."""
    if not text:
        return None
    t = text.strip()
    low = t.lower()
    bad_markers = ("<the person's name", "<their dates", "<a tribute",
                   "as an ai", "i'm sorry", "i am sorry")
    if len(t) < 25 or t.startswith("<") or any(b in low for b in bad_markers):
        return None
    if person["name"].lower() not in low and len(t) < 60:
        # a real tribute almost always names the person; a very short
        # nameless reply is likely an echo or a refusal fragment
        return None
    return t


def fallback_tribute(person: dict) -> str:
    dates = f" ({person['dates']})" if person["dates"] else ""
    place = f" of {person['place']}" if person["place"] else ""
    return (f"In loving memory of {person['name']}{dates}{place}. "
            f"Those who knew them carry their stories forward, and on this "
            f"night of remembrance their light is with us still.")


# -------------------------------------------------------------------- html

CSS = """
body{background:#14100c;color:#f5ead6;font-family:Georgia,'Times New Roman',serif;
margin:0;padding:0;line-height:1.7}
.glow{position:fixed;inset:0;pointer-events:none;
background:radial-gradient(ellipse 60% 40% at 50% 0%,rgba(240,160,48,.14),transparent 70%)}
header{text-align:center;padding:56px 20px 20px}
h1{font-size:2.6em;margin:.2em 0;color:#f7c873;letter-spacing:.04em}
.subtitle{color:#c9a86a;font-style:italic}
.candles{display:flex;justify-content:center;gap:34px;margin:26px 0 8px}
.candle{width:14px;height:64px;background:linear-gradient(#f7e8c8,#e8c78f);
border-radius:6px 6px 3px 3px;position:relative}
.flame{position:absolute;top:-22px;left:50%;width:16px;height:26px;
background:radial-gradient(circle at 50% 70%,#fff6c8 0%,#f7c873 45%,#e07820 80%,transparent 100%);
border-radius:50% 50% 50% 50%/60% 60% 40% 40%;transform:translateX(-50%);
transform-origin:50% 100%;animation:flick 1.6s ease-in-out infinite}
@keyframes flick{0%,100%{transform:translateX(-50%) scale(1) rotate(-2deg)}
50%{transform:translateX(-50%) scale(1.08,1.14) rotate(2deg)}}
main{max-width:720px;margin:0 auto;padding:10px 22px 60px}
.card{background:rgba(247,200,115,.06);border:1px solid rgba(247,200,115,.25);
border-radius:14px;padding:26px 28px;margin:26px 0}
.card h2{margin:0 0 2px;color:#f7c873;font-size:1.6em}
.dates{color:#c9a86a;font-size:.95em;margin-bottom:12px}
.tribute{font-size:1.08em}
blockquote{border-left:3px solid #e07820;margin:18px 0 4px;padding:4px 0 4px 16px;
color:#e8d9bd;font-style:italic}
.engine{font-size:.8em;color:#8a7a5f;margin-top:14px;font-family:monospace}
footer{text-align:center;color:#8a7a5f;font-size:.9em;padding:30px 20px 50px}
.marigold{color:#e07820}
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ofrenda — a night of remembrance</title>
<style>{css}</style>
</head>
<body>
<div class="glow"></div>
<header>
  <div class="candles">{candles}</div>
  <h1>Ofrenda</h1>
  <p class="subtitle">a night of remembrance &mdash; {today}</p>
  <p>On D&iacute;a de los Muertos we set a place for those who came before us.<br>
  These words were written on <span class="marigold">this machine alone</span> &mdash;
  no cloud, no account, no one listening.</p>
</header>
<main>
{cards}
</main>
<footer>
  <p><span class="marigold">&#10086;</span> Built with a local open-weight model.
  Every story on this page never left this computer. <span class="marigold">&#10086;</span></p>
</footer>
</body>
</html>
"""

CARD_TEMPLATE = """<section class="card">
  <h2>{name}</h2>
  <div class="dates">{dates}{place}</div>
  <p class="tribute">{tribute}</p>
  {memory_block}
  <div class="engine">tribute written by: {engine}</div>
</section>
"""


def build_html(people: list[dict]) -> str:
    candles = '<div class="candle"><div class="flame"></div></div>' * 3
    cards = []
    for p in people:
        dates = html.escape(p["dates"]) if p["dates"] else "dates unknown"
        place = f" &middot; {html.escape(p['place'])}" if p["place"] else ""
        if p["memory"]:
            memory_block = (f'<blockquote>&ldquo;{html.escape(p["memory"])}&rdquo;'
                            f"<br>&mdash; kept by the family</blockquote>")
        else:
            memory_block = ""
        cards.append(CARD_TEMPLATE.format(
            name=html.escape(p["name"]), dates=dates, place=place,
            tribute=html.escape(p["tribute"]), memory_block=memory_block,
            engine=html.escape(p["engine"])))
    return HTML_TEMPLATE.format(css=CSS, candles=candles,
                                today=date.today().isoformat(),
                                cards="\n".join(cards))


# -------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Ofrenda Keeper — a local remembrance page")
    ap.add_argument("memories", help="folder of .txt memory files")
    ap.add_argument("--out", default="out", help="output folder")
    ap.add_argument("--model", default="gemma3:1b", help="Ollama model to use")
    args = ap.parse_args(argv)

    mem_dir = Path(args.memories)
    files = sorted(mem_dir.glob("*.txt"))
    if not files:
        print(f"No .txt memory files found in {mem_dir}.")
        print("Run python make_sample_memories.py to create fictional samples.")
        return 1

    print(f"Ofrenda Keeper — weaving {len(files)} remembrance(s)")
    print(f"Model: {args.model} (local, via Ollama) | Today: {date.today().isoformat()}\n")

    people = []
    for f in files:
        person = parse_memory_file(f)
        tribute = clean_tribute(ask_gemma_tribute(args.model, person), person)
        if tribute is None:
            tribute, engine = fallback_tribute(person), "fallback-rules"
        else:
            engine = "gemma-local"
        person["tribute"], person["engine"] = tribute, engine
        people.append(person)
        label = "TRIBUTE" if engine == "gemma-local" else "tribute*"
        print(f"  [{label}] {person['name'][:50]:50} | {engine}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "ofrenda.html").write_text(build_html(people), encoding="utf-8")
    print(f"\nWrote: {out / 'ofrenda.html'}  — open it in your browser.")
    print("* fallback-rules = Ollama was unreachable or the model echoed; "
          "template tribute used, honestly labelled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
