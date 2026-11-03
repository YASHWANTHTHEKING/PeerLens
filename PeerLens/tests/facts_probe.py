import requests

HEADERS = {"User-Agent": "ExamateStudentProject yash123ace@gmail.com"}
r = requests.get("https://data.sec.gov/api/xbrl/companyfacts/CIK0001067491.json", headers=HEADERS, timeout=60)
print(r.status_code)
facts = r.json()["facts"]
print(list(facts.keys()))  # taxonomies, e.g. 'ifrs-full', 'dei'
for tax, concepts in facts.items():
    print(tax, len(concepts), list(concepts)[:15])
