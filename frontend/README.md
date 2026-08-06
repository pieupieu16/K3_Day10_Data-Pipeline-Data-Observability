# Frontend - Day 10 Data Pipeline Console

Giao dien theo phong cach **Windows Forms** de theo doi va dieu khien pipeline cua lab.
Backend chi dung **thu vien chuan cua Python** (`http.server`), khong them dependency nao vao `pyproject.toml`.

## Chay

```powershell
python frontend/server.py
```

Mac dinh mo `http://127.0.0.1:8765` va tu bat trinh duyet.

Tuy chon:

```powershell
python frontend/server.py --port 9000 --host 0.0.0.0 --no-browser
```

Server co the chay bang bat ky Python 3.8+ nao. Rieng **pipeline** duoc chay bang
`.venv\Scripts\python.exe` neu co (nguoc lai dung Python dang chay server), nen hay
`uv sync` hoac tao `.venv` voi Python 3.11-3.13 truoc khi bam nut Run.
Tab **Config** hien phien ban Python dang duoc dung va canh bao neu sai.

## Cac tab

| Tab | Noi dung |
| --- | --- |
| Dashboard | So do luong pipeline, chi so chinh, bang trang thai 16 artifact kem nguoi phu trach |
| Data Explorer | Xem `papers_clean.csv`, `papers_clean_corrupted.csv`, `papers_clean_repaired.csv`, loc va xem chi tiet tung ban ghi |
| Data Quality | Freshness report, cac data quality check trong `data/quality/`, corruption log |
| Metrics | Bang so sanh baseline / corrupted / repaired kem delta, bieu do cot, phan Ragas |
| Evaluation | `test_set.json` va cac file `*_answers.json`, xem cau hoi - cau tra loi - judge |
| Reports | Doc `phase1_report.md` va `corruption_report.md` (co render markdown) |
| Console | Chay pipeline va xem log stdout/stderr theo thoi gian thuc |
| Config | Bien moi truong (da che secret), Python interpreter, bang phan cong nhom |

## Phim tat

| Phim | Chuc nang |
| --- | --- |
| F5 | Lam moi tat ca |
| Shift+F5 | Dung pipeline dang chay |
| F9 | Chay Phase 1 (baseline) |
| F10 | Chay Corruption Flow |
| F1 | Huong dan nhanh |
| Ctrl+1..7 | Chuyen tab |

URL ho tro hash: `http://127.0.0.1:8765/#metrics` mo thang tab Metrics.

## API

Frontend chi doc file trong `data/` va goi hai script trong `script/`; khong sua du lieu.

| Endpoint | Mo ta |
| --- | --- |
| `GET /api/status` | Trang thai ton tai / kich thuoc / thoi diem cap nhat cua tung artifact |
| `GET /api/dataset?name=clean\|corrupted\|repaired&limit&offset` | Doc CSV thanh bang |
| `GET /api/metrics` | Ba file `*_metrics.json` |
| `GET /api/quality` | Moi file JSON trong `data/quality/` + `corruption_log.json` |
| `GET /api/report?name=phase1\|corruption` | Noi dung markdown bao cao |
| `GET /api/testset`, `GET /api/answers?state=...` | Test set va cau tra loi cua agent |
| `GET /api/config` | `.env` (secret da che) + thong tin Python |
| `POST /api/run` `{"pipeline":"phase1"}` | Chay `script/run_phase1.py` hoac `run_corruption_flow.py` |
| `GET /api/run?offset=N` | Poll log va trang thai tien trinh |
| `POST /api/run/stop`, `POST /api/run/clear` | Dung tien trinh / xoa log |

## Luu y

- Khi pipeline chua implement, nut Run se bao `NotImplementedError` trong Console - dung nhu trang thai starter.
- Server chi nen chay o `127.0.0.1`: no cho phep khoi chay tien trinh Python, dung mo ra mang ngoai.
- Cac o trong bang trang thai se tu chuyen sang **OK** sau khi pipeline sinh du file, khong can sua gi o frontend.
