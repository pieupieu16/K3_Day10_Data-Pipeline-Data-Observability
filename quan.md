# Báo cáo Thay đổi (Change Log) - Ingestion Crossref Data

## 1. Tổng quan

File phụ trách: [`src/ingestion/crossref.py`](file:///d:/Vin20k/K3_Day10_Data-Pipeline-Data-Observability/src/ingestion/crossref.py)

Nhiệm vụ đã hoàn thành:
- Gọi API Crossref (`https://api.crossref.org/works`) lấy metadata bài báo khoa học.
- Xử lý retry tự động khi API gặp sự cố (Exponential Backoff với status codes 429, 500, 502, 503, 504, timeout).
- Clean và parse dữ liệu thô sang schema chuẩn `PaperRecord`.
- Lưu trữ các artifact dữ liệu raw theo đúng quy định của dự án.

---

## 2. Chi tiết các thành phần được cài đặt

### 2.1 Schema `PaperRecord`
Định nghĩa dataclass immutable lưu trữ metadata bài báo:
- `paper_id`: Lấy từ DOI chuẩn hóa.
- `title`: Tiêu đề bài báo đã loại bỏ XML/HTML tags.
- `summary`: Tóm tắt/abstract đã làm sạch thẻ JATS XML (`<jats:p>`, ...) và tiền tố `Abstract:`.
- `authors`: Danh sách tên tác giả ghép từ `given` + `family` hoặc `name`.
- `categories` & `primary_category`: Danh sách lĩnh vực/chủ đề từ Crossref `subject`.
- `published` & `updated`: Ngày xuất bản/cập nhật được format theo chuỗi ISO `YYYY-MM-DD`.
- `abs_url` & `pdf_url`: Đòn bẩy URL truy cập bài báo và đường dẫn file PDF (nếu có).
- `comment`: Tên journal/conference (`container-title`) hoặc nhà xuất bản (`publisher`).

### 2.2 Hàm `parse_crossref_payload(payload: dict) -> list[PaperRecord]`
- Lấy danh sách bài báo từ `payload["message"]["items"]`.
- Loại bỏ các bản ghi không hợp lệ (thiếu `DOI` hoặc `title`).
- Hàm bổ trợ `_clean_text`: Sử dụng regex `re.sub(r"<[^>]+>", "", text)` để xóa các thẻ HTML/XML và chuẩn hóa khoảng trắng bằng `normalize_whitespace`.
- Hàm bổ trợ `_extract_date`: Tìm kiếm các trường ngày (`published-online`, `published-print`, `published`, `issued`, `created`) và format thành dạng `YYYY-MM-DD`.
- Trả về danh sách đối tượng `PaperRecord`.

### 2.3 Hàm `fetch_source_records(settings: Settings) -> list[PaperRecord]`
- Xây dựng request parameters từ cấu hình: `query` (`settings.source_query`), `filter` (`settings.source_filter`), `rows` (`settings.max_results`).
- Tự động gọi API và thực hiện retry tối đa 5 lần với thời gian chờ tăng dần (`backoff_factor = 1.5`) khi gặp lỗi rate limit (HTTP 429), lỗi phía máy chủ (5xx) hoặc rớt mạng.
- Ghi raw response thu được vào file [`data/raw/crossref_response.json`](file:///d:/Vin20k/K3_Day10_Data-Pipeline-Data-Observability/data/raw/crossref_response.json).
- Parse response thành danh sách `PaperRecord` và lưu dưới dạng JSON tại [`data/raw/crossref_records.json`](file:///d:/Vin20k/K3_Day10_Data-Pipeline-Data-Observability/data/raw/crossref_records.json).

### 2.4 Hàm `load_raw_records(path: Path) -> list[PaperRecord]`
- Đọc file JSON snapshot (`crossref_records.json`) từ đĩa và khôi phục lại thành danh sách các đối tượng `PaperRecord`.

---

## 3. Đầu ra (Data Artifacts)

- [`data/raw/crossref_response.json`](file:///d:/Vin20k/K3_Day10_Data-Pipeline-Data-Observability/data/raw/crossref_response.json): Chứa nguyên văn JSON payload trả về từ Crossref API.
- [`data/raw/crossref_records.json`](file:///d:/Vin20k/K3_Day10_Data-Pipeline-Data-Observability/data/raw/crossref_records.json): Chứa danh sách các bản ghi bài báo đã parse theo cấu trúc `PaperRecord`.
