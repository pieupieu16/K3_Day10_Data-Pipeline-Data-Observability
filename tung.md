# Báo cáo công việc của Tùng

## Thông tin

- Họ tên: Đỗ Thanh Tùng
- Vai trò: Phụ trách tích hợp pipeline và phát triển frontend cho hệ thống
- Mục tiêu chính: đảm bảo hệ thống chạy end-to-end và có giao diện theo dõi dữ liệu, metrics và reports

## Phạm vi công việc

### 1. Tích hợp pipeline
- Kết nối các module ingestion, cleaning, embedding, evaluation và observability thành pipeline hoàn chỉnh.
- Chịu trách nhiệm chạy baseline pipeline và corruption flow.
- Đảm bảo các artifact được sinh ra đúng thứ tự và dùng chung test set, cấu hình.

### 2. Xây dựng embedding và ChromaDB
- Tạo vector index từ dữ liệu sạch để phục vụ retrieval cho hệ thống RAG.
- Đảm bảo embedding được lưu tại thư mục dữ liệu phù hợp.

### 3. Chạy evaluation và metrics
- Thực hiện đánh giá chất lượng pipeline ở các trạng thái baseline, corrupted và repaired.
- Sinh các file metrics và câu trả lời của agent cho từng trạng thái.

### 4. Phát triển frontend
- Xây dựng giao diện console để theo dõi pipeline.
- Cho phép xem các artifact, metrics, reports, test set, câu trả lời và logs chạy pipeline.
- Hỗ trợ chạy Phase 1 và Corruption Flow trực tiếp từ giao diện.

## File chính tham gia

- src/pipelines/phase1.py
- src/pipelines/corruption_flow.py
- frontend/server.py
- frontend/static/index.html
- frontend/static/app.js
- frontend/static/style.css

## Kết quả mong đợi

- Hệ thống có thể chạy end-to-end từ raw data đến evaluation.
- Người dùng có thể quan sát dữ liệu và kết quả qua frontend.
- Metrics và reports được sinh ra để so sánh hiệu quả giữa các trạng thái dữ liệu.