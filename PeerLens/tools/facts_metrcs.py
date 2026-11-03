import requests

HEADERS = {"User-Agent": "ExamateStudentProject yash123ace@gmail.com"}
r = requests.get("https://data.sec.gov/api/xbrl/companyfacts/CIK0001067491.json", headers=HEADERS, timeout=60)
concepts = r.json()["facts"]["ifrs-full"]

# 1) which concept names look like the metrics you care about?
keys = ["revenue", "profit", "income", "equity", "assets", "cashflow", "operating"]
for k in keys:
    hits = [c for c in concepts if k in c.lower()]
    print(f"\n{k}: {hits[:12]}")

# 2) sample one concept in detail: units and annual values
name = "Revenue" if "Revenue" in concepts else None
if name:
    for unit, rows in concepts[name]["units"].items():
        print("\n", name, unit)
        for row in rows:
            if row.get("form") == "20-F" and row.get("fp") == "FY":
                print(row["end"], row["val"], row.get("fy"))
