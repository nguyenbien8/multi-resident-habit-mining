# Nhật ký thực nghiệm — đợt v1 (25/11/2026)

Ghi lại **mọi quyết định thiết kế** đưa ra trong lúc làm: vấn đề gặp phải, bằng chứng, lựa chọn
cuối cùng. Mục đích: (1) đọc lại để đánh giá; (2) trả lời khi hội đồng hỏi "tại sao chọn như vậy";
(3) biết chỗ nào lệch so với văn bản định nghĩa đề tài (`dinh_nghia_de_tai.md`, cùng thư mục).

Ký hiệu: **[THAY ĐỔI — CẦN XÁC NHẬN]** = lệch so với bản định nghĩa đã chốt.

---

## 1. Môi trường

| Việc | Ghi chú |
|---|---|
| Môi trường Python | `C:\Users\min\.venvs\kltn` (Python 3.11, scikit-learn 1.9.1, pandas 3.1, torch 2.15 CPU) |
| Lý do không dùng `.venv` trong repo | Đường dẫn repo có ký tự tiếng Việt ("KHÓA LUẬN TỐT NGHIỆP") làm `threadpoolctl` không nạp được DLL của numpy/scipy, nên scikit-learn lỗi khi chạy DBSCAN. Venv ở đường dẫn ASCII thì chạy bình thường. Mã nguồn vẫn ở trong repo. |
| LaTeX | Máy không có LaTeX. Khóa luận viết để biên dịch trên Overleaf (pdfLaTeX). Việc tải trình biên dịch Tectonic về máy bị hệ thống chặn nên không thử. |
| Lệnh chạy lại toàn bộ | `PYTHONPATH=src C:\Users\min\.venvs\kltn\Scripts\python.exe -m mrhabits.cli run` rồi `... -m mrhabits.cli figures` |

## 2. Dữ liệu

- Link cũ `casas.wsu.edu/datasets/*.zip` hỏng (HTTP 500). Dùng bản Zenodo 17180309 (33 MB, CC BY 4.0).
  Sơ đồ mặt bằng: Zenodo 15708568 `floorplans.zip`, chỉ có ảnh.
- Kiểm định: 0 dòng lỗi định dạng; có sự kiện lùi thời gian ≤ 0,1 giây → sắp xếp lại.
- Sau lọc ngày (< 20% trung vị): Cairo 56 ngày (bỏ 1), Tulum1 84, Tulum2 137 (bỏ 15), Milan 61 (bỏ 11), Aruba 220.
- **Phát hiện quan trọng:** nhãn gắn người rất ít.
  - Cairo: R1/R2 Wake, Sleep; R1_Work; R2_Take_Medicine (tốt nhất).
  - Tulum1: R1_Snack, R1/R2_Eat_Breakfast.
  - Tulum2: chỉ R1/R2_Sleeping_in_Bed, và hai người ngủ cùng giường (M030 trùng khoảng 56–58%).

  → Trên tập kiểm tra, số thói quen gắn người: Cairo 6, Tulum1 1, Tulum2 1. Cairo là nhà đánh giá
  "từng người" chính; Tulum chủ yếu đóng góp thói quen chung của hộ. Đúng kịch bản rủi ro ở mục 10
  của văn bản định nghĩa.

## 3. Định nghĩa thói quen — thay DBSCAN bằng quét cửa sổ  **[THAY ĐỔI — CẦN XÁC NHẬN]**

**Vấn đề 1 — DBSCAN "chuỗi hóa".** Áp DBSCAN (eps 30 phút) làm thói quen đáp án cho ra các cụm dài
cả ngày với hoạt động lặp nhiều lần: "Personal_Hygiene 09:43–23:49" (Tulum2), "Kitchen_Activity
09:28–20:31" (Milan). Như vậy vi phạm chính định nghĩa ("lệch không quá khoảng 30 phút"). Đây cũng là
hạn chế "phòng khách 14:19–22:20" của đề tài thực tập.

**Vấn đề 2 — HDBSCAN không khớp định nghĩa.** Văn bản định nghĩa chốt H = HDBSCAN. Nhưng ngay cả khi
dùng nhãn thật, HDBSCAN chỉ đạt F1 0,26 (Cairo) và 0,22 (Tulum1) so với định nghĩa; DBSCAN đạt 0,70 và
0,92. HDBSCAN không có khái niệm "30 phút" và cắt vụn cụm.

**Lựa chọn:** hiện thực **đúng nguyên văn định nghĩa** bằng thuật toán quét cửa sổ ±30 phút trên vòng
24 giờ (bước 5 phút), đếm **số ngày phân biệt**, giữ đỉnh ≥ 50% số ngày, khử đỉnh không cực đại (hai
thói quen cùng hoạt động cách nhau ≥ 60 phút). DBSCAN và HDBSCAN giữ lại làm **ablation** để chứng minh
lựa chọn. Hệ quả: Oracle+H = 1,0 theo cấu trúc, nên mọi sai lệch đều đến từ khâu nhận dạng (đúng điều
kiện cần cho phân tích lỗi lan truyền).

**Vấn đề 3 — thói quen riêng cuối tuần nhiễu:** 3/6 ngày cuối tuần đã đạt 50%. Thêm điều kiện ≥ 4 ngày
cho thói quen riêng ngày thường hoặc cuối tuần.

**Lỗi thư viện:** `sklearn.cluster.HDBSCAN` với `cluster_selection_epsilon` + `allow_single_cluster`
gây `TypeError` trong `_tree.pyx` (bug của scikit-learn 1.9.1) → bỏ `cluster_selection_epsilon`.

## 4. So khớp thói quen

Ban đầu so khớp yêu cầu trùng (hoạt động, loại ngày). M1 tìm "R2 uống thuốc 06:57, mọi ngày" còn đáp
án là "07:08, ngày thường" → không được tính. Đổi thành so khớp theo **hoạt động** (Hungary, lệch ≤ 60
phút); loại ngày chỉ ghi lại để tham khảo.

## 5. Cấu trúc nhà từ dữ liệu

- Phân vùng phổ chọn số vùng bằng eigengap; Cairo được 6 vùng, ARI so với 7 vùng đọc từ sơ đồ = 0,70
  (vùng bếp khớp tuyệt đối).
- **Chuyển tiếp giả:** với cửa sổ 10 giây và ngưỡng 2%, M021 (bếp) bị coi là kề M005 (phòng ngủ tầng
  trên), vì hai người hoạt động cùng lúc. Đã thử lưới {2, 5, 10 giây} × {2, 5, 8, 10%} × {hoặc, và}; chọn
  5 giây, 8%, "hoặc", kèm bước nối thành phần → đồ thị liên thông, bậc trung bình khoảng 3,6, M021–M005 =
  5 bước. Lựa chọn dựa trên sơ đồ Cairo, **không** dựa trên kết quả mô hình.

## 6. Baseline B0/B1 — cách gán nhãn cho cụm

Ban đầu dùng nhãn đa số kể cả phiên không nhãn → 9/10 cụm Cairo "không nhãn" (Cairo chỉ gán nhãn
khoảng 2,5 giờ/ngày). Xem bên trong thì thấy B0 **thất bại thật**: vùng bếp thành **một cụm 963 phiên
trải cả ngày** (gộp sáng, trưa, tối, uống thuốc); phiên bị cắt vụn, trung vị 1,8–2,7 phút. Đổi quy tắc:
nhãn đa số **trong các phiên có nhãn**, "không nhãn" khi dưới 20% phiên trùng nhãn. Quy tắc này có lợi
cho baseline.

## 7. Bộ nhận dạng

- **M2 (Bi-GRU)** overfit từ epoch 2. Thử 3 cấu hình, **chọn theo val loss trên Cairo**:
  | hidden | dropout | lr | weight decay | val loss |
  |---|---|---|---|---|
  | **64** | **0,2** | **1e-3** | **0** | **0,3626** |
  | 32 | 0,3 | 5e-4 | 1e-4 | 0,3645 |
  | 32 | 0,5 | 3e-4 | 1e-3 | 0,3772 |

  Sau khi chọn số epoch bằng dừng sớm, huấn luyện lại trên toàn bộ ngày huấn luyện.
- Ngưỡng từng hoạt động chọn trên tập kiểm định (25% số ngày cuối của tập huấn luyện).
- Mô hình dùng cho ablation **cố định là M1**. Ban đầu mã chọn mô hình theo F1 trên tập kiểm tra; đã sửa
  vì như vậy là dùng tập kiểm tra để ra quyết định.

## 8. RQ3 — loại ngày mơ hồ khỏi chấm điểm  **[THAY ĐỔI NHỎ — CẦN XÁC NHẬN]**

Lần chạy đầu: Cairo có trung bình 13,8 ngày bị coi là "bỏ thuốc" trên 22 ngày kiểm tra, trong khi mỗi
lần chỉ cài 3 ngày → khoảng 11 ngày **vốn không có nhãn uống thuốc** trong cửa sổ. Không phân biệt được
"bỏ thuốc thật" với "không ghi nhãn". B2 đạt recall 1,0 chỉ vì báo động gần như mọi ngày.

**Sửa:** chỉ chấm điểm trên các ngày **có uống thuốc thật trong cửa sổ ở dữ liệu gốc**; dương tính =
ngày bị cài, âm tính = ngày còn nguyên; báo cáo riêng số ngày mơ hồ. Đây là thí nghiệm có kiểm soát
đúng nghĩa. Số hạt giống giữ nguyên là 5 như văn bản định nghĩa.

## 9. Kết quả sơ bộ đáng chú ý (sẽ phân tích trong Chương 4)

- Cairo RQ2: B0 0,24; **B1 0,12 (tách vệt theo vị trí làm tệ hơn)**; B2+H 0,43; **M1+H 0,62 (recall
  1,0; thói quen từng người 6/6)**; M2+H 0,37.
- Lỗi lan truyền (Cairo): bỏ sót 20% → F1 0,81; lệch giờ σ 10 phút → 0,98 (gần như vô hại); chèn giả
  50% → 0,97; tráo người 20% → 0,77. → Thói quen **chịu được lệch giờ và nhận thừa**, nhưng **nhạy với bỏ
  sót và nhầm người**.
- Ablation (Cairo, M1): bỏ tách loại ngày cho F1 0,67, nhỉnh hơn 0,62. Cần phân tích thêm ở v2.

## 10. Kết quả cuối đợt v1 (chạy lại toàn bộ bằng mã cuối cùng, 11:17–12:21)

- Toàn bộ 5 nhà chạy bằng **cùng một phiên bản mã**: đã dừng lượt chạy đầu (dùng cách chấm RQ3 cũ) để
  chạy lại từ đầu. Kết quả Cairo trùng khớp hoàn toàn với lần trước, chứng tỏ quy trình tất định.
- RQ2 (F1 thói quen), theo thứ tự Cairo / Tulum1 / Tulum2 / Milan / Aruba:
  - B0: 0,24 / 0,22 / 0,33 / 0,38 / 0,29
  - B1: 0,12 / 0,22 / 0,18 / 0,38 / 0,27
  - B2+H: 0,43 / 0,59 / 0,54 / 0,40 / **0,62**
  - M1+H: **0,62** / 0,71 / 0,50 / 0,54 / 0,59
  - M2+H: 0,37 / **0,75** / 0,51 / **0,55** / 0,50
- **Milan RQ3 không đánh giá được**: thuốc sáng trong giai đoạn huấn luyện có nhãn 19/37 ngày nhưng giờ dao
  động khoảng 08:06–10:25, không có cửa sổ 60 phút nào đạt 50% số ngày; thuốc tối chỉ có 5/37 ngày. Theo
  đúng định nghĩa thì không có thói quen chuẩn. **Không** nới định nghĩa riêng cho một nhà sau khi đã thấy
  kết quả.
- RQ3 Cairo: 10 ngày chấm điểm (12/22 ngày mơ hồ bị loại), 2 ngày cài mỗi lần. B0-vùng và M1 không báo
  động lần nào; M2 recall 0,90, 0,54 báo nhầm/ngày; B2 báo động gần như mọi ngày.
- Đã đối chiếu từng nhận định trong Chương 4 với số liệu cuối: sửa 13 chỗ (xem lịch sử chỉnh sửa).

## 11. Việc gợi ý cho đợt v2

1. Nhiều lần chia theo thời gian → khoảng tin cậy.
2. Giảm thói quen giả (giải mã theo thời lượng; ràng buộc một lần mỗi ngày cho thức dậy, ngủ).
3. Phân tích ma trận nhầm lẫn có hệ thống.
4. RQ3: tìm thêm dữ liệu có uống thuốc; tăng số lần cài.
5. Đọc hai tài liệu mới trong thư mục `Tham khảo` ("Association rules for smart home.pdf", "Energy.pdf")
   để bổ sung Chương 2 nếu liên quan.
