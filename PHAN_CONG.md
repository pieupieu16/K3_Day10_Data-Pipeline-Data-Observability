# Phân công nhóm 5 người

## Bảng thành viên

| Tên | Mã học viên |
| --- | --- |
| Trần Hải Quân | 2A202601521 |
| Nguyễn Thành Long | 2A202601443 |
| Hoàng Hải Dương | 2A202601337 |
| Nguyễn Minh Phương | 2A202601947 |
| Đỗ Thanh Tùng | 2A202601205 |

## Quân – Lấy dữ liệu Crossref

**File phụ trách:** `src/ingestion/crossref.py`

**Nhiệm vụ:**

* Gọi Crossref API.
* Xử lý retry khi API lỗi.
* Parse dữ liệu thành `PaperRecord`.
* Lưu raw response và raw records.

**Đầu ra:**

```text
data/raw/crossref_response.json
data/raw/crossref_records.json
```

---

## Dương – Làm sạch dữ liệu và tạo test set

**File phụ trách:**

```text
src/ingestion/cleaning.py
src/evaluation/testset.py
```

**Nhiệm vụ:**

* Chuẩn hóa title, summary, authors, categories và ngày tháng.
* Loại dữ liệu lỗi và duplicate.
* Tạo `age_days` và `text_for_embedding`.
* Tạo các câu hỏi đánh giá về summary, author, date và category.

**Đầu ra:**

```text
data/clean/papers_clean.csv
data/clean/papers_clean.json
data/eval/test_set.json
```

---

## Long – Kiểm tra chất lượng và viết báo cáo

**File phụ trách:**

```text
src/observability/quality.py
src/observability/reporting.py
```

**Nhiệm vụ:**

* Kiểm tra dữ liệu thiếu, trùng, summary rỗng và dữ liệu quá cũ.
* Tạo freshness report.
* Viết báo cáo baseline và báo cáo so sánh ba trạng thái.

**Đầu ra:**

```text
data/quality/
data/reports/phase1_report.md
data/reports/corruption_report.md
```

---

## Phương – Tạo dữ liệu lỗi và repair

**File phụ trách:** `src/ingestion/corruption.py`

**Nhiệm vụ:**

* Xóa một số record mới.
* Làm rỗng summary.
* Thêm text nhiễu.
* Cắt ngắn title.
* Làm ngày xuất bản cũ đi.
* Thêm duplicate.
* Tạo lại `text_for_embedding`.
* Ghi corruption log.
* Kiểm tra dữ liệu repaired được tạo lại từ raw data.

**Đầu ra:**

```text
data/clean/papers_clean_corrupted.csv
data/clean/papers_clean_repaired.csv
data/results/corruption_log.json
```

---

## Tùng – Tích hợp pipeline và phát triển frontend

**File phụ trách:**

```text
src/pipelines/phase1.py
src/pipelines/corruption_flow.py
frontend/server.py
frontend/static/index.html
frontend/static/app.js
frontend/static/style.css
```

**Nhiệm vụ:**

* Kết nối các module thành pipeline hoàn chỉnh cho baseline và corruption flow.
* Build embedding và ChromaDB để tạo vector index cho hệ thống RAG.
* Chạy RAG evaluation và sinh metrics cho baseline, corrupted và repaired.
* Đảm bảo ba trạng thái dùng cùng test set và cấu hình.
* Xây dựng frontend console để theo dõi artifact, metrics, reports và chạy pipeline từ giao diện.
* Hỗ trợ người dùng xem dữ liệu, chất lượng, đánh giá và log chạy pipeline.

**Đầu ra:**

```text
data/embeddings/papers_embeddings.json
data/results/baseline_metrics.json
data/results/corrupted_metrics.json
data/results/repaired_metrics.json
data/results/*_answers.json
frontend/server.py
```

---

# Thứ tự phối hợp

```text
Người 1 lấy raw data
→ Người 2 làm sạch và tạo test set
→ Người 3 viết quality checks
→ Người 5 chạy baseline
→ Người 4 tạo corruption và repair
→ Người 5 chạy so sánh
→ Người 3 hoàn thiện báo cáo
```

Mỗi người cần viết báo cáo cá nhân về phần mình làm. Cả nhóm phải hiểu luồng:

```text
Crossref → Raw → Clean → Embedding → Evaluation
→ Corruption → Repair → So sánh metrics
```