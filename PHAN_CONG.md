# Phân công nhóm 5 người

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

## Quân – Làm sạch dữ liệu và tạo test set

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

## Tùng – Tích hợp và chạy toàn bộ pipeline

**File phụ trách:**

```text
src/pipelines/phase1.py
src/pipelines/corruption_flow.py
```

**Nhiệm vụ:**

* Kết nối các module thành pipeline hoàn chỉnh.
* Build embedding và ChromaDB.
* Chạy RAG evaluation.
* Sinh metrics cho baseline, corrupted và repaired.
* Đảm bảo ba trạng thái dùng cùng test set và cấu hình.
* Kiểm tra toàn bộ artifact trước khi nộp.

**Đầu ra:**

```text
data/results/baseline_metrics.json
data/results/corrupted_metrics.json
data/results/repaired_metrics.json
data/results/*_answers.json
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