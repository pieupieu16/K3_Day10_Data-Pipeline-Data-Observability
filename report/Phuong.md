# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Minh Phương |
| MSSV | 2A202601947 |
| Khóa/Lớp | K3 |
| Tên nhóm | Nhóm 1 |
| Vai trò chính | Corruption/Repair |
| Repository | [K3_Day10_Data-Pipeline-Data-Observability](https://github.com/pieupieu16/K3_Day10_Data-Pipeline-Data-Observability) |
| Ngày hoàn thành | 2026-08-06 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |

| Data corruption | `src/ingestion/corruption.py` — `corrupt_clean_dataframe()` | Clean baseline dataframe | Corrupted dataframe và corruption log | Hoàn thành |
| Corruption/repair orchestration | `src/pipelines/corruption_flow.py` — `run_corruption_flow()` | Baseline artifacts, raw snapshot và test set | Corrupted/repaired data, index, answers, metrics và report | Hoàn thành |
| Corruption verification | `tests/test_corruption.py`, `tests/test_corruption_report.py` | Dataframe/test metrics mẫu | Kiểm tra tính tái lập, validation và report delta | Hoàn thành |
| Documentation | `quan.md`, report cá nhân | Code và artifact thực tế | Tài liệu mô tả cách triển khai và kết quả | Hoàn thành |

### Phần sử dụng từ module của thành viên khác

Corruption flow là phần điều phối nên sử dụng các interface chung thay vì cài đặt lại:

- `build_clean_dataframe()` từ module Cleaning để tái tạo repaired dataset.
- `LocalEmbeddingIndex.build()` từ module RAG để tạo collection corrupted/repaired.
- `evaluate_pipeline()` từ module Evaluation để chấm cùng một test set.
- `run_data_quality_checks()` và `build_freshness_report()` từ module Observability.
- `generate_corruption_report()` từ module Reporting để tổng hợp bằng chứng.

---

## 3. Kết quả theo vai trò


### Corruption có kiểm soát

Từ 24 clean records, tôi tạo sáu loại corruption với seed cố định `42`:

| Corruption | Số target | Mục đích mô phỏng |
| --- | ---: | --- |
| Drop latest records | 4 | Mất dữ liệu và giảm retrieval coverage |
| Blank summary | 3 | Lỗi completeness |
| Inject summary noise | 3 | Nội dung embedding bị nhiễu |
| Truncate title | 3 | Metadata sai và exact lookup suy giảm |
| Stale publication date | 3 | Lỗi freshness |
| Duplicate rows | 2 | Lỗi uniqueness |

Kết quả theo 24 `paper_id` baseline:

- 4 paper bị xóa.
- 8 paper bị sửa.
- 1 paper bị duplicate.
- 1 paper vừa bị sửa vừa duplicate.
- 10 paper giữ nguyên.

Sau khi xóa 4 dòng và thêm 2 duplicate, corrupted dataset có 22 dòng và 20 `paper_id` duy nhất. Bốn paper bị xóa đều thuộc test set, tương ứng 16/40 câu hỏi mất ground-truth document.

Artifact:

```text
data/clean/papers_clean_corrupted.json
data/clean/papers_clean_corrupted.csv
data/results/corruption_log.json
data/results/baseline_corrupted_comparison.csv
```

### Repair và recovery

Repair không đảo ngược corruption bằng tay. Pipeline đọc lại raw snapshot, chạy cùng cleaning rules, tạo lại embedding/index rồi đánh giá lại:

```text
crossref_records.json
→ load_raw_records()
→ build_clean_dataframe()
→ papers_clean_repaired.json
→ papers-repaired collection
→ repaired answers/metrics
```

File repaired clean có cùng hash với clean baseline; repaired answers cũng có cùng hash với baseline answers. Điều này chứng minh recovery tái tạo đúng trạng thái baseline trong lần chạy hiện tại.

---

## 4. Giải thích kỹ thuật


### 4.2 Corruption contract

Hàm `corrupt_clean_dataframe()` thực hiện deep copy nên không mutate baseline. Mỗi lỗi được ghi lại theo `paper_id`, loại corruption và tham số. Sau khi sửa title, summary hoặc published date, hàm tạo lại `summary_chars` và `text_for_embedding` theo đúng contract của cleaning baseline.

Seed `42` được dùng để cùng input sẽ chọn cùng record trong các bước ngẫu nhiên. Nhờ đó corruption, metrics và report có thể tái hiện được.

### 4.3 Experiment contract

Để comparison công bằng, ba trạng thái giữ nguyên:

```text
test set
ground truth
embedding model
retrieval top-k
evaluator
```

Chỉ dataset/index thay đổi. Ba collection riêng được sử dụng:

```text
papers-baseline
papers-corrupted
papers-repaired
```

Điều này tránh ghi đè baseline hoặc trộn document giữa các trạng thái.

### 4.4 Repair contract

Repair phụ thuộc vào raw snapshot đáng tin cậy, cùng cleaning code và configuration. Baseline không phải input để tạo repaired data; baseline chỉ là control dùng để kiểm tra mức phục hồi:

```text
Raw → cleaning → Baseline
Baseline → corruption → Corrupted
Raw → cleaning lại → Repaired
```

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần chọn cách phục hồi sau khi clean data bị xóa, sửa, làm stale và duplicate.
- **Phương án A:** Đọc corruption log rồi sửa ngược từng record.
- **Phương án B:** Copy clean baseline thành repaired dataset.
- **Phương án C:** Reprocess từ raw snapshot bằng cùng cleaning pipeline.
- **Phương án chọn:** Phương án C.
- **Lý do:** Raw snapshot là source of truth, có thể khôi phục cả record đã bị xóa, tránh bỏ sót lỗi và không làm đẹp metrics bằng thao tác thủ công. Đây cũng là cách gần với recovery trong pipeline production.
- **Bằng chứng:** Repaired clean dataset và answers có hash giống baseline; toàn bộ metrics trở lại đúng giá trị baseline.

---

## 6. Một lỗi đã phát hiện và xử lý

- **Triệu chứng:** Lần so sánh đầu tiên cho thấy hầu như mọi retained record đều bị đánh dấu `text_for_embedding` thay đổi, kể cả record không nằm trong corruption log.
- **Nguyên nhân:** Hàm rebuild embedding text ban đầu sử dụng thứ tự field khác cleaning baseline và thiếu nhãn `Published`.
- **Cách xử lý:** Đồng bộ `_embedding_text()` với contract của `build_clean_dataframe()` theo thứ tự `Title`, `Authors`, `Categories`, `Published`, `Summary` và chuẩn hóa whitespace giống baseline.
- **Cách xác minh:** Chạy lại comparison cho kết quả hợp lý: 14/24 paper ID bị tác động và 10/24 paper ID giữ nguyên hoàn toàn.
- **Điều học được:** Failure injection phải chỉ thay đổi đúng target; nếu transformation contract khác baseline, experiment sẽ bị confounded và không thể quy metric delta cho corruption.

---

## 7. Kết quả baseline–corrupted–repaired

### Data quality và RAG metrics

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.5250 | 1.0000 | Giảm 0.4750 rồi phục hồi hoàn toàn |
| `mean_token_f1` | 0.5777 | 0.3951 | 0.5777 | Giảm 0.1826 rồi trở lại baseline |
| `judge_accuracy` | 0.5250 | 0.3750 | 0.5250 | Giảm 0.1500 rồi trở lại baseline |
| `mean_judge_score` | 3.0500 | 2.4500 | 3.0500 | Giảm 0.6000 rồi trở lại baseline |
| Data quality | PASS | FAIL | PASS | Corrupted có duplicate IDs và invalid summaries |
| Freshness | FRESH | STALE | FRESH | Stale rows thay đổi `0 → 4 → 0` |
| Row count | 24 | 22 | 24 | Repair phục hồi đủ records |

### Diễn giải

Retrieval hit rate giảm mạnh nhất, từ `1.0` xuống `0.525`, vì bốn ground-truth papers bị loại khỏi corrupted index và một số metadata/content bị thay đổi. Khi repair từ raw, clean corpus và index được tái tạo nên retrieval hit rate trở lại `1.0`.

Mean Token F1 baseline chỉ đạt `0.5777`, không phải `1.0`, do hai giới hạn của QA/evaluation hiện tại:

- Câu hỏi summary có ground truth là toàn bộ abstract nhưng QA chỉ trả về câu đầu tiên.
- Pattern `Who are the authors...` chưa được `_extract_answer()` nhận diện nên trả về summary thay vì authors.

Đây không phải lỗi do corruption. Mục tiêu của experiment là đo delta trên cùng evaluator; corrupted F1 giảm xuống `0.3951` và repaired trở lại đúng baseline `0.5777`.

### Giới hạn evaluator

LLM judge không khả dụng trong lần chạy này. Cả 40 samples ở mỗi trạng thái sử dụng heuristic fallback dựa trên Token F1; Ragas cũng được skip vì `RUN_RAGAS` chưa bật. Vì vậy `judge_accuracy` và `mean_judge_score` không được trình bày như kết quả LLM-as-a-judge thực sự.

Artifact bằng chứng:

```text
data/results/baseline_metrics.json
data/results/corrupted_metrics.json
data/results/repaired_metrics.json
data/results/baseline_answers.json
data/results/corrupted_answers.json
data/results/repaired_answers.json
data/quality/corrupted_quality.json
data/quality/repaired_quality.json
data/reports/corruption_report.md
```

---

## 8. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Raw artifact là nền tảng của recovery:** Nếu chỉ giữ clean/index, record đã bị xóa hoặc sửa sai sẽ khó phục hồi đáng tin cậy.
2. **Observability phải nối upstream với downstream:** Missing, duplicate và stale signals chỉ thực sự có ý nghĩa khi liên hệ được với retrieval/answer metrics.
3. **Comparison phải kiểm soát biến:** Cùng test set, model, top-k và evaluator là điều kiện để kết luận metric thay đổi do dữ liệu.

### Nếu có thêm thời gian

- Sửa pattern author question và căn chỉnh summary ground truth để baseline evaluation phản ánh QA chính xác hơn.
- Chạy LLM judge thật và bật Ragas để bổ sung semantic/faithfulness metrics.
- Lưu baseline run date/version cùng artifact để `age_days` có thể tái tạo byte-for-byte khi repair chạy ở ngày khác.
- Đưa quality gates vào CI để pipeline dừng trước khi index một batch dữ liệu không đạt chuẩn.

---

## 9. Cam kết của thành viên

- [x] Nội dung phản ánh đúng phần việc và artifact thực tế.
- [x] Các số liệu baseline–corrupted–repaired khớp với JSON metrics.
- [x] Báo cáo phân biệt rõ code sở hữu và module sử dụng từ thành viên khác.
- [x] Báo cáo ghi rõ giới hạn heuristic judge và Ragas chưa chạy.
- [x] Không chứa `.env`, API key, token hoặc secret.

**Họ và tên:** Nguyễn Minh Phương  
**Ngày xác nhận:** 2026-08-06
