# Định nghĩa đề tài khóa luận tốt nghiệp (bản chốt phạm vi)

| | |
|---|---|
| Sinh viên | Nguyễn Văn Biển — 23021477 — QH-2023-I/CQ-I-CS3 |
| Giảng viên hướng dẫn | TS. Vũ Thị Hồng Nhạn |
| Ngày chốt | 25/11/2026 |
| Trạng thái | **Đã chốt.** Mọi thay đổi theo quy tắc ở mục 11 |

---

## 1. Tên đề tài

- **Tiếng Việt:** Học thói quen sinh hoạt của từng cư dân trong nhà thông minh nhiều người từ dữ liệu cảm biến môi trường
- **Tiếng Anh:** Learning per-resident daily habits from ambient sensors in multi-resident smart homes

## 2. Vấn đề

Nhà thông minh dùng cảm biến môi trường (chuyển động, nhiệt độ, cửa) để theo dõi sinh hoạt mà không cần camera. Khi trong nhà có **hai người**, cảm biến không biết ai đã kích hoạt nó. Vì vậy các phương pháp tìm thói quen dành cho nhà một người, như phương pháp ở kỳ thực tập (gom phiên theo phòng × giờ rồi phân cụm DBSCAN), sẽ trộn thói quen của hai người với nhau.

Ví dụ trong bộ dữ liệu CASAS Cairo (một cặp vợ chồng, 57 ngày):

| Hoạt động | Giờ trung vị | Cảm biến kích hoạt nhiều nhất |
|---|---|---|
| R1 thức dậy | 6:44 | M005, M001 |
| R2 thức dậy | 7:04 | M005, M009 |
| **R2 uống thuốc** | **7:20** | **M021, M024 (bếp)** |
| Ăn sáng | 7:29 | M024, M021 (bếp) |

Thói quen uống thuốc và bữa sáng dùng chung cảm biến bếp và chỉ cách nhau khoảng 10 phút. Gom theo phòng × giờ không thể tách hai thói quen này.

Khóa luận giải bài toán: **từ luồng cảm biến trộn lẫn, tìm đúng thói quen của từng người**, và chứng minh thói quen tìm được dùng được để **phát hiện ngày bỏ thuốc**.

## 3. Phát biểu bài toán

**Đầu vào**
- Chuỗi sự kiện cảm biến của một nhà 2 người. Mỗi sự kiện gồm thời điểm, mã cảm biến và giá trị. Không có thông tin ai kích hoạt.
- Nhãn hoạt động có gắn người (ví dụ `R2_Take_Medicine`), **chỉ của các ngày huấn luyện**.

**Đầu ra.** Với mỗi người, một danh sách thói quen. Mỗi thói quen gồm:
- ai (R1, R2, hoặc "chung" nếu nhãn gốc không gắn người)
- hoạt động gì
- giờ điển hình (trung bình vòng tròn) và khung giờ chứa 80% số lần
- thời lượng trung vị
- tần suất = số ngày xuất hiện / số ngày quan sát; tách riêng ngày thường và cuối tuần

**Định nghĩa thói quen.** Một thói quen là tập các lần thực hiện **cùng một hoạt động, bởi cùng một người**, có giờ bắt đầu lệch nhau không quá khoảng 30 phút, xuất hiện ở **ít nhất 50% số ngày** quan sát.

**Thói quen đáp án.** Áp đúng định nghĩa trên lên nhãn thật của các ngày kiểm tra. Đáp án chỉ dùng để đánh giá, không đưa vào mô hình.

## 4. Câu hỏi nghiên cứu (cố định 3 câu)

| | Câu hỏi | Vai trò |
|---|---|---|
| **RQ1** | Gán các đoạn sự kiện cảm biến cho **đúng người và đúng hoạt động** chính xác đến đâu? | Bước đầu vào |
| **RQ2** | Từ kết quả RQ1, thói quen của từng người tìm được **đúng đến đâu so với đáp án**? Lỗi ở RQ1 ảnh hưởng thế nào đến thói quen? | **Lõi, đóng góp chính** |
| **RQ3** | Thói quen tìm được có phát hiện được **ngày bỏ thuốc** không? | Ứng dụng chứng minh giá trị |

## 5. Ý nghĩa và giá trị mong đợi

**Khoa học**
1. Nối hai nhóm nghiên cứu đang tách rời. Nhóm nhận dạng hoạt động nhà nhiều người (Chen 2021; sMRT 2020; MDP 2026) dừng ở câu hỏi "ai đang làm gì". Nhóm khai phá mẫu sinh hoạt (DISCOVER 2025; đề tài thực tập) chỉ kiểm chứng trên nhà một người.
2. Đổi thước đo đánh giá từ "từng cửa sổ sự kiện" sang **"thói quen"**: đưa ra định nghĩa đo được và bộ chỉ số so thói quen tìm được với đáp án.
3. **Đo lỗi lan truyền**: nhận dạng sai bao nhiêu thì thói quen sai bấy nhiêu? Chưa có công trình nào làm điều này.
4. Đánh giá chia theo ngày, khắc phục rủi ro rò rỉ dữ liệu của cách 10-fold không theo thời gian.

**Thực tiễn**
- Việt Nam già hóa nhanh: năm 2024 có khoảng 14,2 triệu người cao tuổi (khoảng 14% dân số), dự kiến thành dân số già khoảng 2034–2036. Việc chăm sóc chủ yếu do người thân đảm nhận.
- Người cao tuổi thường sống cùng vợ hoặc chồng hay con cháu. Hệ thống chỉ chạy được cho nhà một người không dùng được trong những ngôi nhà như vậy.
- WHO (2003): tuân thủ điều trị bệnh mạn tính trung bình chỉ khoảng 50%. Phát hiện bỏ thuốc là lõi thuật toán cho các hệ thống nhắc thuốc sau này.
- Chỉ dùng cảm biến môi trường: không camera, không thiết bị đeo, tôn trọng quyền riêng tư.

**Không hứa:** dùng được ngay cho nhà thật ở Việt Nam; vượt kết quả tốt nhất thế giới về nhận dạng hoạt động; phát hiện bất thường thật (bất thường được cài vào dữ liệu); gán người cho từng sự kiện.

## 6. Dữ liệu (đã chốt và đã kiểm định)

Nguồn: CASAS, Đại học Bang Washington, bản trên Zenodo (record 17180309, tệp `new_labeled_data.zip`), giấy phép CC BY 4.0.

| Bộ dữ liệu | Số người | Số ngày | Vai trò |
|---|---|---|---|
| **Cairo** | 2 | 57 | Chính: RQ1, RQ2, RQ3 (có `R2_Take_Medicine` 44 ngày) |
| **Tulum1** | 2 | 84 (trên khoảng 121) | Chính: RQ1, RQ2 |
| **Tulum2** | 2 | 152 (trên khoảng 185) | Chính: RQ1, RQ2 |
| Milan | 1 | 72 | Phụ: RQ3 (`Morning_Meds`, `Eve_Meds`) |
| Aruba | 1 | 220 | Phụ: đối chứng với kết quả thực tập |

Kiểm định ngày 25/11/2026:
- 0 dòng lỗi định dạng.
- Có sự kiện lùi thời gian, nhưng tối đa 0,1 giây.
- Cairo đủ ngày, không có khoảng trống.
- Tulum có ngày thiếu và khoảng trống dài hơn 3 giờ.

**Quy tắc xử lý (cố định)**
- Sắp xếp lại theo thời gian.
- Bỏ các ngày có số sự kiện dưới 20% trung vị.
- Nhãn không có tiền tố `R1_` hoặc `R2_` được coi là hoạt động **chung của hộ**.

**Chia dữ liệu (cố định):** theo thứ tự thời gian. **60% số ngày đầu để huấn luyện, 40% số ngày sau để kiểm tra.** Không xáo trộn ngẫu nhiên.

## 7. Phương pháp (danh sách cố định)

| Mã | Thành phần | Mô tả |
|---|---|---|
| **B0** | Baseline thực tập | Phiên theo phòng × giờ + DBSCAN, không tách người |
| **B1** | Baseline heuristic | Tách luồng theo vị trí cảm biến (ý tưởng chương 3 của Chen 2021) + khai phá thói quen như B0 |
| **M1** | Mô hình học cổ điển | Cửa sổ sự kiện → đặc trưng (cảm biến, giờ, thời lượng, chuyển phòng) → **Random Forest** dự đoán (người, hoạt động) |
| **M2** | Mô hình học chuỗi | Chuỗi sự kiện → **Bi-GRU** dự đoán (người, hoạt động) |
| **H** | Khai phá thói quen | Với mỗi (người, hoạt động): giờ trên vòng tròn, phân cụm **HDBSCAN**, lọc theo ngưỡng 50% số ngày, tách ngày thường và cuối tuần |
| **A** | Phát hiện bỏ thuốc | Đến cuối khung giờ của thói quen (khung 80% cộng 30 phút) mà chưa thấy lần thực hiện nào thì báo động |
| **Oracle** | Trường hợp lý tưởng | Dùng nhãn thật thay cho đầu ra RQ1, làm giới hạn trên |

So sánh B0, B1, M1+H, M2+H và Oracle+H trên cùng tập kiểm tra.

## 8. Đánh giá và tiêu chí hoàn thành

| Câu hỏi | Chỉ số | Hoàn thành khi |
|---|---|---|
| RQ1 | Accuracy, macro-F1 cho (người, hoạt động) trên tập kiểm tra | Có bảng so sánh B1, M1, M2 trên 3 nhà 2 người |
| RQ2 | Precision, recall, F1 của thói quen so với đáp án; sai số giờ (phút); sai số tần suất | Có bảng so sánh B0, B1, M1, M2, Oracle; có phân tích lỗi lan truyền |
| RQ3 | Xóa sự kiện trong các lần `R2_Take_Medicine` ở 20% số ngày kiểm tra (5 hạt giống ngẫu nhiên) → precision, recall, F1, báo động nhầm mỗi ngày, độ trễ phát hiện | Có kết quả trên Cairo và Milan |
| Chung | Ablation (bỏ tách người, bỏ tách ngày thường và cuối tuần, HDBSCAN → DBSCAN); độ nhạy (ngưỡng 50%, khoảng 30 phút) | Có bảng và hình |

Không đặt mục tiêu "phải vượt X%". Khóa luận đạt yêu cầu khi các so sánh được làm đúng cách, tái lập được, và có phân tích nguyên nhân.

## 9. Phạm vi (khóa cứng)

**Trong phạm vi**
- Nhà 2 người, dữ liệu công khai CASAS như mục 6.
- Các phương pháp B0, B1, M1, M2, H, A, Oracle như mục 7.
- Đánh giá ngoại tuyến (offline), chia theo ngày.
- Mã nguồn Python có kiểm thử, tái lập được; khóa luận LaTeX (Overleaf); slide; báo cáo tiến độ.

**Ngoài phạm vi** (chỉ nhắc trong hướng phát triển)
- Hình ảnh, camera, thiết bị đeo.
- LLM, foundation model, học tự giám sát.
- Nhà từ 3 người trở lên; tự thu thập dữ liệu.
- Gán người cho **từng sự kiện**.
- Học trực tuyến, trôi khái niệm.
- Dự đoán hành động tiếp theo.
- Ứng dụng nhắc nhở thật, giao diện người dùng, điều khiển thiết bị, robot.
- Tối ưu để vượt SOTA về nhận dạng hoạt động.

## 10. Rủi ro và phương án dự phòng

| Rủi ro | Xử lý đã chốt |
|---|---|
| M2 không tốt hơn M1 | Vẫn báo cáo; thói quen dùng mô hình tốt hơn trong hai mô hình |
| Một nhà có quá ít thói quen gắn với từng người | Đánh giá trên các hoạt động có tiền tố; phần còn lại báo cáo là thói quen chung của hộ |
| Không đủ ngày để phát hiện bỏ thuốc | Tăng số lần cài với hạt giống khác nhau; bổ sung Milan |
| Thiếu thời gian | Ưu tiên: RQ2 > RQ1 > RQ3 > ablation. M2 là phần đầu tiên được cắt |

## 11. Quy tắc thay đổi phạm vi

Một thay đổi chỉ được chấp nhận khi đồng thời:
1. giúp trả lời RQ1, RQ2 hoặc RQ3;
2. không làm trễ mốc thời gian;
3. được sinh viên và giảng viên hướng dẫn đồng ý.

Mọi ý tưởng khác ghi vào mục "Hướng phát triển".

## 12. Quy trình làm việc và sản phẩm mỗi đợt

Xác định hướng → nghiên cứu, phát triển → viết khóa luận hoàn chỉnh → sản phẩm. Sản phẩm mỗi đợt gồm:
- **Khóa luận vN** (LaTeX, thư mục `thesis/`, biên dịch trên Overleaf)
- **Slide**
- **Báo cáo tiến độ** cho GVHD để cập nhật và xác nhận hướng đi

Sau mỗi đợt: đọc kỹ lại → đánh giá → phát triển hoặc tìm hiểu chi tiết thêm.

## 13. Mốc thời gian dự kiến

| Thời gian | Kết quả bàn giao |
|---|---|
| 11–12/2026 | **Đợt v1:** dữ liệu, toàn bộ quy trình, thực nghiệm đầu tiên, khóa luận v1, slide, báo cáo tiến độ |
| 1–2/2027 | Đợt v2: hoàn thiện theo góp ý của GVHD, phân tích sâu lỗi lan truyền |
| 3/2027 | Đợt v3: ablation, độ nhạy, hoàn thiện RQ3 |
| 4/2027 | Hoàn thiện văn bản |
| 5/2027 | Bản nộp, slide bảo vệ |

## 14. Các quyết định mặc định (chờ xác nhận lại nếu muốn đổi)

- Giữ cả hai mô hình M1 (Random Forest) và M2 (Bi-GRU).
- Chia dữ liệu 60/40 theo thời gian.
- Viết khóa luận bằng **tiếng Việt**.
- Repo `khoa-luan-tot-nghiep` **chỉ chứa khóa luận**; mỗi đợt bàn giao trong một thư mục `vN/`.

## 15. Đề xuất thay đổi phát sinh trong đợt v1 (chờ SV và GVHD xác nhận)

Theo quy tắc ở mục 11, hai thay đổi dưới đây giúp trả lời RQ2/RQ3, không làm trễ tiến độ, và **đang chờ
xác nhận**. Bằng chứng chi tiết ở `nhat_ky_thuc_nghiem.md` (cùng thư mục).

| # | Mục bị ảnh hưởng | Thay đổi | Bằng chứng |
|---|---|---|---|
| 1 | Mục 7, thành phần H | Khai phá thói quen bằng **thuật toán quét cửa sổ** (hiện thực đúng nguyên văn định nghĩa) thay cho HDBSCAN; DBSCAN và HDBSCAN chuyển thành ablation | Trên nhãn thật, HDBSCAN khớp định nghĩa ở mức F1 0,22–0,75; DBSCAN 0,38–0,92 |
| 2 | Mục 8, RQ3 | Chỉ chấm điểm trên ngày **có uống thuốc thật** trong dữ liệu gốc; ngày mơ hồ báo cáo riêng | 12/22 ngày kiểm tra của Cairo không có nhãn uống thuốc |

Ghi nhận thêm (không phải thay đổi phạm vi): RQ3 trên Milan không đánh giá được vì giờ uống thuốc không đủ
đều để tạo thói quen chuẩn theo định nghĩa.
