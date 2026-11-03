# Dataset

Source: SEC EDGAR annual reports (Form 20-F) filed by Infosys Limited, CIK
0001067491. Downloaded files are kept in `data/raw/` and are excluded from Git.
The page counts below are explicit `page-break-after` markers detected in the
SEC HTML. The parser numbers the resulting page sections from 1; those numbers
may differ from printed pagination.

| File | Fiscal year | Source URL | Page-break markers | Terms |
|---|---:|---|---:|---|
| `infy-20f_20220331.htm` | 2022 | https://www.sec.gov/Archives/edgar/data/1067491/000156459022023521/infy-20f_20220331.htm | 245 | SEC.gov access policy; no separate reuse licence asserted |
| `infy-20230331.htm` | 2023 | https://www.sec.gov/Archives/edgar/data/1067491/000095017023028187/infy-20230331.htm | 241 | SEC.gov access policy; no separate reuse licence asserted |
| `infy-20240331.htm` | 2024 | https://www.sec.gov/Archives/edgar/data/1067491/000095017024076649/infy-20240331.htm | 236 | SEC.gov access policy; no separate reuse licence asserted |
| `infy-20250331.htm` | 2025 | https://www.sec.gov/Archives/edgar/data/1067491/000095017025091925/infy-20250331.htm | 241 | SEC.gov access policy; no separate reuse licence asserted |
| `infy-20260331.htm` | 2026 | https://www.sec.gov/Archives/edgar/data/1067491/000119312526270520/infy-20260331.htm | 256 | SEC.gov access policy; no separate reuse licence asserted |
| **Total** | | | **1,219** | |

Respect the SEC's fair-access policy when fetching filings. This project records
the source URLs and does not treat public availability as a separate licence
grant. The local downloader records download date, byte count, and a SHA-256
prefix in `data/manifest.csv`.

The current raw corpus is local-only. Re-download it with
`python tools/download.py urls.txt` after configuring an appropriate contact
identity in the downloader.
