# Bàn giao đợt v1 — 25/11/2026

Thư mục `v1/` là **toàn bộ sản phẩm bàn giao của đợt 1**. Mở thư mục này là đủ. Các thư mục khác của repo
(`src/`, `thesis/`, `slides/`, `results/`…) là nơi làm việc để sinh ra các sản phẩm này.

## 1. Có gì trong `v1/`

| Tệp | Là gì | Dùng thế nào |
|---|---|---|
| `khoa_luan_v1_overleaf.zip` | Khóa luận LaTeX (5 chương, phụ lục, 36 tài liệu tham khảo, 6 hình, 12 bảng) | Overleaf → **New Project → Upload Project** → chọn tệp này → Settings: Compiler **pdfLaTeX**, Main document `main.tex` → Recompile |
| `slide_v1.pdf` | Slide báo cáo (17 trang, 16:9, nền sáng) | Mở bằng trình đọc PDF; nhấn F5 hoặc chế độ toàn màn hình để thuyết trình |
| `bao_cao_tien_do_v1.docx` | Báo cáo tiến độ gửi giảng viên hướng dẫn (kèm bản `.md`) | Gửi cô; cuối báo cáo có mục "Em xin ý kiến cô" |
| `dinh_nghia_de_tai.md` | Định nghĩa đề tài, phạm vi đã chốt; mục 15 ghi 2 đề xuất thay đổi | Đối chiếu khi muốn thêm/bớt việc |
| `nhat_ky_thuc_nghiem.md` | Mọi quyết định thiết kế: vấn đề, bằng chứng, lựa chọn | Đọc trước khi bảo vệ để trả lời "vì sao làm vậy" |
| `BAN_GIAO_v1.md` | Tệp này | |

## 2. Nên đọc theo thứ tự

1. `bao_cao_tien_do_v1.docx` — tổng quan trong 3 trang.
2. `slide_v1.pdf` — câu chuyện của đề tài.
3. `dinh_nghia_de_tai.md` — phạm vi, câu hỏi nghiên cứu.
4. Khóa luận: Chương 1 → Chương 4 (kết quả) → Chương 3 (phương pháp) → Chương 2.
5. `nhat_ky_thuc_nghiem.md` — vì sao chọn như vậy.

## 3. Kết quả chính

- Cách tiếp cận theo vùng (B0) **thất bại** trên nhà hai người: vùng bếp Cairo thành một cụm 963 phiên.
- **Random Forest + định nghĩa thói quen**: F1 thói quen 0,50–0,71 so với 0,22–0,33 của B0 ở nhà hai người;
  Cairo đủ **6/6 thói quen từng người**, kể cả "R2 uống thuốc 06:57".
- Thói quen **chịu được** lệch giờ nhỏ và chèn giả ngẫu nhiên; **nhạy** với bỏ sót, nhầm người, lỗi có hệ
  thống. Lỗi chính hiện tại: **thói quen giả**.
- Phát hiện bỏ thuốc: Bi-GRU 9/10 ngày nhưng 0,54 báo nhầm/ngày; Random Forest và B0 không phát hiện được.
- Tách luồng theo vị trí (B1, ý tưởng của Chen) **không giúp**, còn làm tệ hơn — một kết quả âm có giá trị.

## 4. Chạy lại toàn bộ (tái lập số liệu)

```bash
# Môi trường Python ở đường dẫn không dấu: C:\Users\min\.venvs\kltn
set PYTHONPATH=src
C:/Users/min/.venvs/kltn/Scripts/python.exe -m pytest                 # 20 kiểm thử
C:/Users/min/.venvs/kltn/Scripts/python.exe -m mrhabits.cli run       # khoảng 1 giờ, 5 nhà -> results/
C:/Users/min/.venvs/kltn/Scripts/python.exe -m mrhabits.cli figures   # hình + bảng -> thesis/
```

Slide: sửa `slides/slides_v1.html`, rồi mở bằng Microsoft Edge → In (Ctrl+P) → "Lưu dưới dạng PDF", tắt
"Đầu trang và chân trang", bật "Đồ họa nền".

## 5. Việc bạn cần làm

1. **Xác nhận 2 đề xuất thay đổi** (`dinh_nghia_de_tai.md`, mục 15), rồi gửi cô báo cáo tiến độ.
2. **Biên dịch khóa luận trên Overleaf** bằng tệp `.zip`. Máy không có LaTeX nên chưa biên dịch thật; đã
   kiểm tra tĩnh (tham chiếu, trích dẫn, hình, môi trường đều khớp). Nếu Overleaf báo lỗi, gửi dòng lỗi.
3. **Thêm logo UET** vào bìa (xem `thesis/README.md`).
4. **Tạo repo GitHub riêng** khi muốn: repo đã có git (nhánh `main`), chưa có commit và chưa có remote.
5. Đọc phần **"Mối đe dọa tính hợp lệ"** (cuối Chương 4) — hội đồng hay hỏi.

## 6. Hạn chế, lưu ý

- Mới có **một lần chia** dữ liệu → chưa có khoảng tin cậy.
- Dữ liệu ARAS và CASAS twor không tải được.
- RQ3 chỉ đánh giá được trên Cairo, mẫu nhỏ (10 ngày dương tính qua 5 lần cài).
- Lời cam đoan có đoạn khai báo sử dụng trợ lý AI — chỉnh theo quy định của trường.
- Thư mục `Tham khảo` (ngoài repo) có 2 tài liệu chưa đọc: "Association rules for smart home.pdf", "Energy.pdf".

## 7. Đợt tiếp theo (v2)

Bàn giao trong thư mục `v2/`. Việc dự kiến: nhiều lần chia theo thời gian (khoảng tin cậy); giảm thói quen
giả; phân tích nhầm lẫn có hệ thống; tìm thêm dữ liệu.
