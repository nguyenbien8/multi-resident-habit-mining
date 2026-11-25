---
title: "Báo cáo khóa luận tốt nghiệp — bản v1"
subtitle: "Học thói quen sinh hoạt của từng cư dân trong nhà thông minh nhiều người từ dữ liệu cảm biến môi trường"
author: "Nguyễn Văn Biển — 23021477 — QH-2023-I/CQ-I-CS3"
date: "Hà Nội, 25/11/2026"
lang: vi
---

**Kính gửi:** TS. Vũ Thị Hồng Nhạn

Em xin báo cáo cô bản v1 của khóa luận. Bản này đã hoàn chỉnh về nội dung: khóa luận 5 chương bằng LaTeX,
slide trình bày và mã nguồn tái lập toàn bộ số liệu. Báo cáo gồm định hướng đề tài, phương pháp, kết quả
chính, **hai điểm em xin cô xác nhận** và một số câu hỏi xin ý kiến cô.

Mã nguồn: <https://github.com/nguyenbien8/multi-resident-habit-mining>

# 1. Định hướng đề tài

**Từ thực tập đến khóa luận.** Đề tài thực tập tìm thói quen từ cảm biến bằng cách gom phiên theo phòng rồi
phân cụm DBSCAN, nhưng ngầm giả định trong nhà chỉ có một người. Thực tế người cao tuổi thường sống cùng
vợ/chồng hoặc con cháu, và cảm biến môi trường không biết ai đã kích hoạt nó. Luận án của Dong Chen (AUT, 2021)
giải bài toán nhận dạng hoạt động trong nhà nhiều người, nhưng dừng ở *hoạt động hiện tại*; chính luận án nêu
đây là hạn chế.

**Bài toán.** Từ luồng cảm biến trộn lẫn của nhà hai người, tìm đúng **thói quen của từng người**, và dùng
thói quen để **phát hiện ngày bỏ thuốc**.

| | Câu hỏi nghiên cứu |
|---|---|
| RQ1 | Gán sự kiện cảm biến cho đúng (người, hoạt động) chính xác đến đâu? |
| RQ2 | Thói quen từng người tìm được đúng đến đâu? Lỗi nhận dạng lan truyền sang thói quen thế nào? *(trung tâm)* |
| RQ3 | Thói quen có phát hiện được ngày bỏ thuốc không? |

**Phạm vi.** Trong phạm vi: nhà 2 người, dữ liệu công khai CASAS, đánh giá ngoại tuyến chia theo ngày. Ngoài
phạm vi: camera, mô hình ngôn ngữ lớn, nhà từ 3 người, tự thu dữ liệu, học trực tuyến, ứng dụng nhắc nhở thật.

**Khoảng trống.** Các công trình về nhà nhiều người (Chen 2021; sMRT 2021; Chen, Cumin và cộng sự 2026) dừng ở
mức sự kiện hoặc hoạt động; các công trình về mẫu sinh hoạt (DISCOVER 2025) mới làm với nhà một người. Chưa có
công trình nào học và đánh giá thói quen của từng người trong nhà nhiều người.

# 2. Phương pháp

| Thành phần | Nội dung |
|---|---|
| Dữ liệu | 5 nhà CASAS (bản công bố lại trên Zenodo, CC BY 4.0): Cairo, Tulum1, Tulum2 (2 người); Milan, Aruba (1 người, đối chứng). Chỉ dùng sự kiện cảm biến chuyển động; chia 60% ngày đầu huấn luyện, 40% ngày sau kiểm tra. |
| Định nghĩa thói quen | Hoạt động *a* của một người có thói quen quanh giờ *c* nếu ở ≥ 50% số ngày, *a* bắt đầu trong [c − 30′, c + 30′]. Hiện thực bằng thuật toán **quét cửa sổ** đếm theo ngày. |
| Cấu trúc nhà | Đồ thị kề cảm biến và các vùng rút ra từ chính dữ liệu (không cần sơ đồ); trên Cairo khớp sơ đồ thật ở mức ARI 0,75. |
| Nhận dạng | B2 (tra bảng vùng × giờ), M1 (Random Forest, 20 sự kiện, có đặc trưng "nhảy xa" báo hiệu hai người), M2 (Bi-GRU, 30 sự kiện); sau đó giải mã thành các lần thực hiện và áp định nghĩa thói quen. |
| Baseline | B0 = phương pháp thực tập (phiên theo vùng + DBSCAN); B1 = B0 + tách luồng theo vị trí (ý tưởng của Chen). |
| Đánh giá | Thói quen đáp án (định nghĩa áp lên nhãn thật), so khớp Hungary, P/R/F1; đánh giá qua nhiều lần chia; làm nhiễu nhãn có kiểm soát để đo lỗi lan truyền; cài ngày bỏ thuốc. |

# 3. Kết quả chính

**F1 của thói quen tìm được so với thói quen đáp án (lần chia 60/40)**

| Phương pháp | Cairo | Tulum1 | Tulum2 | Milan | Aruba |
|---|---|---|---|---|---|
| B0 – phương pháp thực tập | 0,24 | 0,22 | 0,33 | 0,38 | 0,29 |
| B1 – + tách luồng theo vị trí | 0,12 | 0,22 | 0,18 | 0,38 | 0,27 |
| B2+H – tra bảng | 0,43 | 0,59 | 0,54 | 0,40 | **0,63** |
| **M1+H – Random Forest** | **0,62** | 0,71 | 0,50 | 0,54 | 0,59 |
| M2+H – Bi-GRU | 0,37 | **0,75** | 0,51 | **0,55** | 0,50 |

1. **Phương pháp thực tập không dùng được cho nhà hai người.** Ở Cairo, hai người đi lại xen kẽ làm phiên bị
   cắt vụn; DBSCAN gộp ăn sáng, trưa, tối và uống thuốc ở vùng bếp thành **một cụm 963 phiên**. Tách luồng
   theo vị trí (B1) không cứu được, còn làm tệ hơn.
2. **Học (người, hoạt động) rồi áp định nghĩa thói quen tốt hơn hẳn:** F1 0,50–0,71 so với 0,22–0,33 ở nhà
   hai người. Ở Cairo, Random Forest tìm **đủ 6/6 thói quen gắn với từng người**, kể cả *"R2 uống thuốc 06:57"*
   (đáp án 07:08), vốn trùng giờ và trùng cảm biến với bữa sáng.
3. **Kết quả giữ khi đổi lần chia.** Đánh giá lại ba nhà hai người qua 8 lần chia theo thời gian: F1 trung bình
   M1+H 0,57, B2+H 0,53, M2+H 0,53, B0 0,26. M1+H cao hơn B0 ở **7/8 lần chia** (kiểm định Wilcoxon,
   p = 0,016). Độ dao động giữa các lần chia lớn (độ lệch chuẩn tới 0,24) vì mỗi lần chỉ có 11–28 ngày kiểm tra.
4. **Lỗi lan truyền.** Thói quen chịu được lệch giờ nhỏ (σ = 10 phút → F1 0,98) và chèn giả ngẫu nhiên, nhưng
   nhạy với bỏ sót (20% → 0,81) và nhầm người (20% → 0,77).
5. **Thói quen giả.** Truy ngược 11 thói quen giả của Random Forest ở Cairo: phần lớn là "đuôi" ngay sau một
   thói quen thật (ăn sáng 08:16 cạnh 07:15) hoặc rơi vào khoảng không có nhãn (8/11). Mức quan trọng đặc trưng
   cho thấy mô hình dựa nhiều vào **giờ trong ngày** (0,43 tổng mức quan trọng).
6. **Phát hiện bỏ thuốc (Cairo):** Bi-GRU phát hiện 9/10 ngày bỏ thuốc được cài nhưng còn 0,54 báo động nhầm mỗi
   ngày; Random Forest và cách theo vùng không phát hiện được ngày nào.
7. **Nhận dạng theo sự kiện (RQ1)** đạt macro-F1 0,38–0,49 — thấp hơn các báo cáo thường thấy vì em chia dữ liệu
   theo thời gian thay vì 10-fold ngẫu nhiên, để tránh rò rỉ dữ liệu.

# 4. Hai điểm em xin cô xác nhận

So với bản định nghĩa đề tài đã chốt, có hai thay đổi phát sinh từ bằng chứng thực nghiệm:

1. **Khâu khai phá thói quen dùng thuật toán quét cửa sổ thay cho HDBSCAN.** Ngay trên nhãn thật, HDBSCAN chỉ
   khớp định nghĩa thói quen ở mức F1 0,22–0,75 và DBSCAN ở mức 0,38–0,92. Quét cửa sổ hiện thực đúng nguyên văn
   định nghĩa. HDBSCAN và DBSCAN được giữ làm thí nghiệm so sánh.
2. **RQ3 chỉ chấm điểm trên ngày có uống thuốc thật trong dữ liệu gốc.** 12/22 ngày kiểm tra của Cairo không có
   nhãn uống thuốc, nên không phân biệt được "bỏ thuốc thật" với "không ghi nhãn". Ở Milan, giờ uống thuốc dao
   động quá rộng nên không tạo được thói quen chuẩn; RQ3 vì vậy chỉ đánh giá được trên Cairo.

# 5. Hạn chế

- **Nhãn gắn người ít.** Đánh giá "từng người" chủ yếu dựa trên Cairo (6 thói quen); mỗi nhà Tulum chỉ có 1.
- **Ít ngày kiểm tra** nên kết quả dao động; đánh giá nhiều lần chia mới làm cho ba nhà hai người.
- **Mẫu RQ3 nhỏ** (10 ngày dương tính qua 5 lần cài), bất thường là bất thường được cài.
- Bộ dữ liệu ARAS (nhà 2 người) không truy cập được.

# 6. Em xin ý kiến cô

1. Cô có đồng ý với hai thay đổi ở mục 4 không ạ?
2. Kết quả RQ3 mới đánh giá được trên một nhà. Cô thấy giữ RQ3 như hiện tại (ghi rõ hạn chế) là đủ, hay em nên
   tìm thêm dữ liệu có hoạt động uống thuốc?
3. Về hình thức: khóa luận em viết bằng tiếng Việt theo mẫu của trường; cô có yêu cầu gì thêm không ạ?

Em xin cảm ơn cô!

*Sinh viên: Nguyễn Văn Biển*
