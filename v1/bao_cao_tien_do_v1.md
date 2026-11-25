---
title: "Báo cáo tiến độ khóa luận tốt nghiệp — đợt 1"
subtitle: "Học thói quen sinh hoạt của từng cư dân trong nhà thông minh nhiều người từ dữ liệu cảm biến môi trường"
author: "Nguyễn Văn Biển — 23021477 — QH-2023-I/CQ-I-CS3"
date: "Hà Nội, 25/11/2026"
lang: vi
---

**Kính gửi:** TS. Vũ Thị Hồng Nhạn

Em xin báo cáo cô kết quả đợt làm việc đầu tiên của khóa luận, gồm: định hướng đề tài đã chốt, những gì
đã làm được, kết quả thực nghiệm chính, **hai điểm em xin cô xác nhận** và kế hoạch đợt tiếp theo. Kèm
theo báo cáo là khóa luận bản v1 (LaTeX, 5 chương) và slide.

# 1. Định hướng đề tài

**Từ thực tập đến khóa luận.** Đề tài thực tập tìm thói quen từ cảm biến bằng cách gom phiên theo phòng
rồi phân cụm DBSCAN, nhưng ngầm giả định trong nhà chỉ có một người. Thực tế người cao tuổi thường sống
cùng vợ/chồng hoặc con cháu, và cảm biến môi trường không biết ai đã kích hoạt nó. Luận án của Dong Chen
(AUT, 2021) mà cô giao đọc giải bài toán nhận dạng hoạt động trong nhà nhiều người, nhưng dừng ở
*hoạt động hiện tại*; chính luận án nêu đây là hạn chế.

**Bài toán khóa luận.** Từ luồng cảm biến trộn lẫn của nhà hai người, tìm đúng **thói quen của từng
người**, và dùng thói quen để **phát hiện ngày bỏ thuốc**.

**Ba câu hỏi nghiên cứu**

| | Câu hỏi |
|---|---|
| RQ1 | Gán sự kiện cảm biến cho đúng (người, hoạt động) chính xác đến đâu? |
| RQ2 | Thói quen từng người tìm được đúng đến đâu? Lỗi nhận dạng lan truyền sang thói quen thế nào? *(trung tâm)* |
| RQ3 | Thói quen có phát hiện được ngày bỏ thuốc không? |

**Phạm vi.**

- *Trong phạm vi:* nhà 2 người; dữ liệu công khai CASAS; đánh giá ngoại tuyến, chia dữ liệu theo ngày.
- *Ngoài phạm vi:* camera; mô hình ngôn ngữ lớn; nhà từ 3 người; tự thu dữ liệu; học trực tuyến; dự đoán
  hành động; ứng dụng nhắc nhở thật; robot.

**Khoảng trống.** Các công trình về nhà nhiều người (Chen 2021; sMRT 2021; Chen, Cumin và cộng sự,
IMWUT 2026) dừng ở mức sự kiện hoặc hoạt động. Các công trình về mẫu sinh hoạt (DISCOVER 2025) mới làm với
nhà một người. Chưa có công trình nào học và đánh giá thói quen của từng người trong nhà nhiều người.

# 2. Những việc đã làm

| Hạng mục | Kết quả |
|---|---|
| Dữ liệu | Link tải cũ của CASAS đã hỏng; tìm được bản công bố lại trên Zenodo (CC BY 4.0) và kiểm định 5 nhà: Cairo, Tulum1, Tulum2 (2 người); Milan, Aruba (1 người). |
| Định nghĩa thói quen | Phát biểu hình thức và hiện thực bằng thuật toán *quét cửa sổ* đếm theo ngày. |
| Phương pháp | B0 (phương pháp thực tập), B1 (+ tách luồng theo vị trí, ý tưởng chương 3 của Chen), B2 (tra bảng), M1 (Random Forest), M2 (Bi-GRU), Oracle (giới hạn trên). |
| Đánh giá | Thói quen đáp án, so khớp Hungary; phân tích lỗi lan truyền bằng làm nhiễu nhãn có kiểm soát; thí nghiệm cài ngày bỏ thuốc. |
| Mã nguồn | Gói Python `mrhabits` (10 module, 20 kiểm thử tự động); tái lập toàn bộ số liệu bằng một lệnh. |
| Văn bản | Khóa luận v1 bằng LaTeX (5 chương, phụ lục, 36 tài liệu tham khảo), slide Beamer. |

# 3. Kết quả chính

**F1 của thói quen tìm được so với thói quen đáp án**

| Phương pháp | Cairo | Tulum1 | Tulum2 | Milan | Aruba |
|---|---|---|---|---|---|
| B0 – phương pháp thực tập | 0,24 | 0,22 | 0,33 | 0,38 | 0,29 |
| B1 – + tách luồng theo vị trí | 0,12 | 0,22 | 0,18 | 0,38 | 0,27 |
| B2+H – tra bảng | 0,43 | 0,59 | 0,54 | 0,40 | **0,62** |
| **M1+H – Random Forest** | **0,62** | 0,71 | 0,50 | 0,54 | 0,59 |
| M2+H – Bi-GRU | 0,37 | **0,75** | 0,51 | **0,55** | 0,50 |

1. **Phương pháp thực tập không dùng được cho nhà hai người.** Ở Cairo, hai người đi lại xen kẽ làm phiên
   bị cắt vụn; DBSCAN gộp ăn sáng, trưa, tối và uống thuốc ở vùng bếp thành **một cụm 963 phiên**. Tách luồng
   theo vị trí (B1) không cứu được, còn làm tệ hơn.
2. **Học (người, hoạt động) rồi áp định nghĩa thói quen tốt hơn hẳn:** F1 0,50–0,71 so với 0,22–0,33 ở nhà
   hai người. Ở Cairo, Random Forest tìm **đủ 6/6 thói quen gắn với từng người**, kể cả *"R2 uống thuốc
   06:57"* (đáp án 07:08), vốn trùng giờ và trùng cảm biến với bữa sáng.
3. **Lỗi lan truyền.** Thói quen chịu được lệch giờ nhỏ (σ = 10 phút → F1 0,98) và chèn giả ngẫu nhiên,
   nhưng nhạy với bỏ sót (20% → 0,81) và nhầm người (20% → 0,77). Lỗi chính của mô hình hiện tại là
   **thói quen giả do nhầm lẫn có hệ thống**.
4. **Phát hiện bỏ thuốc (Cairo):** Bi-GRU phát hiện 9/10 ngày bỏ thuốc được cài nhưng còn 0,54 báo động nhầm
   mỗi ngày; Random Forest và cách theo vùng không phát hiện được ngày nào.
5. **Nhận dạng theo sự kiện (RQ1)** đạt macro-F1 0,38–0,49. Con số này thấp hơn các báo cáo thường thấy vì
   em chia dữ liệu theo thời gian thay vì 10-fold ngẫu nhiên, để tránh rò rỉ dữ liệu.

# 4. Hai điểm em xin cô xác nhận

So với bản định nghĩa đề tài đã chốt, có hai thay đổi phát sinh từ bằng chứng thực nghiệm:

1. **Khâu khai phá thói quen dùng thuật toán quét cửa sổ thay cho HDBSCAN.**
   Ngay trên nhãn thật, HDBSCAN chỉ khớp định nghĩa thói quen ở mức F1 0,22–0,75 và DBSCAN ở mức 0,38–0,92
   (DBSCAN "chuỗi hóa" thành các cụm dài cả ngày). Quét cửa sổ hiện thực đúng nguyên văn định nghĩa
   ("lệch không quá 30 phút, ít nhất 50% số ngày"). HDBSCAN và DBSCAN được giữ làm thí nghiệm ablation.
2. **RQ3 chỉ chấm điểm trên ngày có uống thuốc thật trong dữ liệu gốc.**
   12/22 ngày kiểm tra của Cairo không có nhãn uống thuốc, nên không phân biệt được "bỏ thuốc thật" với
   "người chú thích không ghi nhãn". Ở Milan, giờ uống thuốc dao động quá rộng nên không tạo được thói
   quen chuẩn; vì vậy RQ3 hiện chỉ đánh giá được trên Cairo.

# 5. Khó khăn và hạn chế hiện tại

- **Nhãn gắn người ít.** Đánh giá "từng người" chủ yếu dựa trên Cairo (6 thói quen); mỗi nhà Tulum chỉ có 1.
- **Mẫu RQ3 nhỏ** (10 ngày dương tính qua 5 lần cài).
- **Mới có một lần chia dữ liệu**, chưa có khoảng tin cậy.
- Trang tải bộ dữ liệu ARAS (nhà 2 người, dùng trong luận án Chen) không truy cập được từ máy của em.

# 6. Kế hoạch đợt 2 (12/2026 – 2/2027)

1. Đánh giá qua nhiều lần chia theo thời gian (cửa sổ trượt) để có khoảng tin cậy và kiểm định thống kê.
2. Giảm thói quen giả: giải mã theo thời lượng điển hình của từng hoạt động, ràng buộc "mỗi người một lần
   thức dậy mỗi ngày".
3. Phân tích nhầm lẫn có hệ thống (uống thuốc ↔ ăn sáng; R1 ↔ R2).
4. Xin thêm dữ liệu ARAS hoặc CASAS Kyoto nếu có thể.
5. Hoàn thiện văn bản theo góp ý của cô.

# 7. Em xin ý kiến cô

1. Cô có đồng ý với hai thay đổi ở mục 4 không ạ?
2. Kết quả RQ3 mới đánh giá được trên một nhà. Cô thấy giữ RQ3 như hiện tại (ghi rõ hạn chế) là đủ, hay em
   nên tìm thêm dữ liệu có hoạt động uống thuốc?
3. Cô có thể giúp em liên hệ để xin bộ dữ liệu ARAS được không ạ?
4. Về hình thức: khóa luận em đang viết bằng tiếng Việt theo mẫu của trường; cô có yêu cầu gì thêm không ạ?

Em xin cảm ơn cô!

*Sinh viên: Nguyễn Văn Biển*
