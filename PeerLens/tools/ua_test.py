import requests

HEADERS = {"User-Agent": "ExamateStudentProject yash123ace@gmail.com"}

# Infosys's CIK is 1067491
r = requests.get(
    "https://data.sec.gov/submissions/CIK0001067491.json",
    headers=HEADERS,
    timeout=30,
)
print(r.status_code)
r.raise_for_status()

recent = r.json()["filings"]["recent"]

for form, acc, doc, d in zip(
    recent["form"],
    recent["accessionNumber"],
    recent["primaryDocument"],
    recent["filingDate"],
    strict=True,
):
    if form == "20-F":
        url = f"https://www.sec.gov/Archives/edgar/data/1067491/{acc.replace('-', '')}/{doc}"
        print(d, url)
