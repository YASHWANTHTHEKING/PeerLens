"""
Polite downloader: python tools/download.py urls.txt
urls.txt: one URL per line (lines starting with # are skipped).
Saves files to data/raw/ and logs every file to data/manifest.csv.
"""

import csv
import hashlib
import os
import sys
import time
from datetime import date
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

RAW = "data/raw"
MANIFEST = "data/manifest.csv"

# Default identity. Infosys's WAF returns 403 when an email address is
# inside the UA, so contact info goes in the standard From header.
HEADERS = {
    "User-Agent": "ExamateStudentProject/1.0 (learning project)",
    "From": "yash123ace@gmail.com",
}

# SEC's fair-access policy asks for a contact email in the User-Agent.
SEC_HEADERS = {
    "User-Agent": "ExamateStudentProject yash123ace@gmail.com",
}

DELAY = 2  # seconds between requests

robots = {}


def headers_for(url):
    host = urlparse(url).netloc
    return SEC_HEADERS if host.endswith("sec.gov") else HEADERS


def load_robots(root):
    """Fetch robots.txt with OUR headers (RobotFileParser.read() would
    use Python-urllib's UA, which CDNs often reject with 403)."""
    rp = RobotFileParser()
    try:
        r = requests.get(root + "/robots.txt", headers=headers_for(root), timeout=15)
    except requests.RequestException:
        return None  # unreachable: proceed carefully

    if r.status_code == 200:
        rp.parse(r.text.splitlines())
    elif r.status_code in (401, 403):
        rp.disallow_all = True  # server refuses us: respect that
    else:
        rp.allow_all = True  # 404 etc.: no robots.txt
    return rp


def allowed(url):
    root = "{0.scheme}://{0.netloc}".format(urlparse(url))

    if root not in robots:
        robots[root] = load_robots(root)

    rp = robots[root]
    ua = headers_for(url)["User-Agent"]
    return rp is None or rp.can_fetch(ua, url)


def name_for(url):
    name = os.path.basename(urlparse(url).path) or "index.html"
    return name.replace(" ", "_")


def main(list_file):
    os.makedirs(RAW, exist_ok=True)

    new_manifest = not os.path.exists(MANIFEST)

    with open(MANIFEST, "a", newline="") as mf:
        log = csv.writer(mf)

        if new_manifest:
            log.writerow(["file", "source_url", "downloaded_on", "bytes", "sha256"])

        with open(list_file) as fh:
            urls = [u.strip() for u in fh]

        for url in urls:
            if not url or url.startswith("#"):
                continue

            path = os.path.join(RAW, name_for(url))

            if os.path.exists(path):
                print("skip (already have)", path)
                continue

            if not allowed(url):
                print("BLOCKED by robots.txt, not downloading:", url)
                continue

            try:
                r = requests.get(url, headers=headers_for(url), timeout=60)
            except requests.RequestException as e:
                print("error", e, url)
                continue

            if r.status_code != 200:
                print("failed", r.status_code, url)
                time.sleep(DELAY)
                continue

            with open(path, "wb") as f:
                f.write(r.content)

            digest = hashlib.sha256(r.content).hexdigest()[:16]

            log.writerow([path, url, date.today().isoformat(), len(r.content), digest])
            mf.flush()

            print("saved", path, len(r.content), "bytes")

            time.sleep(DELAY)


if __name__ == "__main__":
    main(sys.argv[1])
