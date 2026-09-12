# Healthcare monthly summary + upload dedupe — tasks

- [x] Backend: DELETE /health/uploads/<uuid>/ (uploader-or-staff)
- [x] Backend: GET /health/summary/ (monthly aggregates, all kinds)
- [x] Router entry
- [x] Frontend: SummaryPanel (monthly + YTD FY + ITD, per-kind columns, dup badge)
- [x] Frontend: delete button + confirm + refresh
- [x] Local checks: py_compile + tsc
- [x] Deploy backend + frontend on prod
- [x] Live verify: summary endpoint + delete of Tlamelo's 2 duplicate revenue uploads
- [x] Browser smoke on omni.alphadirect.co.bw/healthcare/revenue
- [x] Email reply to Tlamelo (omni@ via Graph), cc EXCO
