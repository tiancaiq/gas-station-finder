import re
from pathlib import Path

INPUT = "output.md"   # paste that big text into this file
OUT = "zips.txt"

text = Path(INPUT).read_text(encoding="utf-8", errors="ignore")

# Find any 5-digit ZIP codes
zips = re.findall(r"\b\d{5}\b", text)

# Deduplicate and sort
zips = sorted(set(zips))

with open(OUT, "w", encoding="utf-8") as f:
    for z in zips:
        f.write(z + "\n")

print(f"✅ Extracted {len(zips)} ZIP codes → {OUT}")
