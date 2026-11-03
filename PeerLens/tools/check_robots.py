from urllib.robotparser import RobotFileParser

import requests

UA = "ExamateStudentProject/1.0 (learning project)"
url = "https://www.infosys.com/investors/reports-filings.html"

r = requests.get("https://www.infosys.com/robots.txt", headers={"User-Agent": UA}, timeout=15)
print("status:", r.status_code)
print("content-type:", r.headers.get("content-type"))
print(r.text[:1500])

rp = RobotFileParser()
if r.status_code == 200:
    rp.parse(r.text.splitlines())
print("disallow_all:", rp.disallow_all, "| allow_all:", rp.allow_all)
print("can_fetch:", rp.can_fetch(UA, url))
