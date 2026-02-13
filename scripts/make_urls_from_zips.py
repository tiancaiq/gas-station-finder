import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

TEMPLATE_URL = "https://www.gasbuddy.com/home?search=92617&fuel=1&method=all&maxAge=0"
ZIP_FILE = "zips.txt"      # one zip per line
OUT_FILE = "urls.txt"

def build_url_with_zip(template_url: str, zip_code: str) -> str:
    parts = urlparse(template_url)
    qs = parse_qs(parts.query)

    # replace only the search param
    qs["search"] = [zip_code]

    new_query = urlencode(qs, doseq=True)
    return urlunparse((parts.scheme, parts.netloc, parts.path, "", new_query, ""))

# Load ZIPs
zips = []
for line in Path(ZIP_FILE).read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    m = re.search(r"\b\d{5}\b", line)
    if m:
        zips.append(m.group(0))

zips = sorted(set(zips))

# Write URLs
with open(OUT_FILE, "w", encoding="utf-8") as f:
    for z in zips:
        f.write(build_url_with_zip(TEMPLATE_URL, z) + "\n")

print(f"✅ Wrote {len(zips)} URLs to {OUT_FILE}")
