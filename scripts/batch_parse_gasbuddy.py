import re
import csv
from pathlib import Path

MD_DIR = Path("batch_markdown")
OUT = "stations_all.csv"

H2_STOP = re.compile(r"^\*\s*\*\s*\*\s*$")
NAME_IN_BRACKETS = re.compile(r"\[([^\]]+)\]")
PRICE_RE = re.compile(r"^\$\s*\d+\.\d{2}\s*$")
STREET_RE = re.compile(r"^\d+\s+.+$")


CITY_STATE_RE = re.compile(r"^[A-Za-z .'-]+,\s*[A-Z]{2}$")

def parse_markdown(text: str):
    stations = []
    current = None
    pending_street = None

    def start_station(h3_line: str):
        m = NAME_IN_BRACKETS.search(h3_line)
        name = m.group(1).strip() if m else h3_line.replace("###", "").strip()
        return {"name": name, "address": "N/A", "price": "N/A"}
    prev_line = None
    start = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # stop reading when you see ##
        if start and H2_STOP.match(line):
            start = False
            break
        if line.startswith("## Regular Gas"):
            start = True
        if line.startswith("### "):
            if current:
                stations.append(current)
            current = start_station(line)
            pending_street = None
            continue

        if current is None:
            continue

        if current["price"] == "N/A" and PRICE_RE.match(line):
            current["price"] = line.replace(" ", "")
            continue

        if CITY_STATE_RE.match(line):
            if prev_line and current["address"] == "N/A":
                current["address"] = f"{prev_line}, {line}"
            prev_line = line
            continue
        prev_line = line
        # if pending_street and current["address"] == "N/A" and CITY_STATE_RE.match(line):
        #     current["address"] = f"{pending_street}, {line}"
        #     pending_street = None
        #     continue

    if current:
        stations.append(current)

    return stations

rows = []

for md_file in sorted(MD_DIR.glob("*.md")):
    text = md_file.read_text(encoding="utf-8", errors="ignore")
    stations = parse_markdown(text)
    for s in stations:
        s["source_url_file"] = ""
        rows.append(s)

# OPTIONAL: remove N/A prices
# rows = [r for r in rows if r["price"] != "N/A"]

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["name", "address", "price", "source_url_file"])
    w.writeheader()
    w.writerows(rows)

print(f"✅ Wrote {len(rows)} stations to {OUT}")
