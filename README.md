# Học thói quen sinh hoạt của từng cư dân trong nhà thông minh nhiều người

| | |
|---|---|
| **Đề tài** | Học thói quen sinh hoạt của từng cư dân trong nhà thông minh nhiều người từ dữ liệu cảm biến môi trường |
| **Loại** | Khóa luận tốt nghiệp, ngành Khoa học máy tính, UET-VNU |
| **Sinh viên** | Nguyễn Văn Biển |
| **Giảng viên hướng dẫn** | TS. Vũ Thị Hồng Nhạn |
| **Trạng thái** | Bản v1 (11/2026) — khóa luận 5 chương, slide, báo cáo tiến độ |

Khi trong nhà có hai người, cảm biến môi trường (chuyển động, cửa, nhiệt độ) không biết ai đã kích hoạt
nó. Khóa luận tìm **thói quen của từng người** từ luồng sự kiện trộn lẫn đó. Ví dụ: *"R2 uống thuốc
khoảng 07:08 các ngày thường"*, tách khỏi *"ăn sáng chung khoảng 07:15"* dù hai việc dùng cùng cảm biến
bếp. Sau đó dùng thói quen để **phát hiện ngày bỏ thuốc**.

Đề tài phát triển từ đề tài thực tập "Học thói quen của con người trong ngôi nhà thông minh". Dự án thực
tập là một dự án **riêng**, không thuộc repo này. Tài liệu định hướng chính: luận án tiến sĩ của Dong
Chen (AUT, 2021) về nhận dạng hoạt động trong nhà nhiều người.

## Ba câu hỏi nghiên cứu

| | Câu hỏi |
|---|---|
| RQ1 | Gán các đoạn sự kiện cảm biến cho đúng **(người, hoạt động)** chính xác đến đâu? |
| RQ2 | Thói quen của từng người tìm được đúng đến đâu so với đáp án? Lỗi nhận dạng lan truyền sang thói quen thế nào? |
| RQ3 | Thói quen có phát hiện được ngày bỏ thuốc không? |

## Cài đặt

Python 3.10+. **Trên Windows**, nếu đường dẫn thư mục có ký tự tiếng Việt, hãy tạo môi trường ảo ở một
đường dẫn chỉ gồm ký tự ASCII (ví dụ `C:\Users\<tên>\.venvs\kltn`). `threadpoolctl` của scikit-learn
không nạp được DLL qua đường dẫn có dấu.

```bash
python -m venv C:/Users/<tên>/.venvs/kltn
C:/Users/<tên>/.venvs/kltn/Scripts/python -m pip install -e ".[dev]"
```

## Dữ liệu

Tải `new_labeled_data.zip` (33 MB, giấy phép CC BY 4.0) từ
[Zenodo 17180309](https://zenodo.org/records/17180309) và đặt vào `data/raw/casas/`. Gồm 5 nhà: Cairo,
Tulum1, Tulum2 (2 người), Milan, Aruba (1 người).

## Chạy lại toàn bộ

```bash
python -m mrhabits.cli run        # thực nghiệm 5 nhà -> results/<nhà>/  (khoảng 1 giờ trên CPU)
python -m mrhabits.cli figures    # bảng LaTeX và hình -> thesis/tables, thesis/figures
python -m pytest                  # kiểm thử
```

## Cấu trúc

```text
v1/               BẢN BÀN GIAO ĐỢT 1 — mở thư mục này trước
  khoa_luan_v1_overleaf.zip   khóa luận LaTeX, tải thẳng lên Overleaf
  slide_v1.pdf                slide báo cáo
  bao_cao_tien_do_v1.docx     báo cáo tiến độ gửi giảng viên hướng dẫn (kèm .md)
  BAN_GIAO_v1.md              hướng dẫn bàn giao: đọc gì, chạy lại thế nào, việc cần làm
  dinh_nghia_de_tai.md        định nghĩa đề tài, phạm vi đã chốt
  nhat_ky_thuc_nghiem.md      mọi quyết định thiết kế kèm lý do
src/mrhabits/     mã nguồn (đọc dữ liệu, cấu trúc nhà, nhận dạng, thói quen, baseline,
                  lỗi lan truyền, phát hiện bỏ thuốc, chạy thực nghiệm, sinh hình/bảng)
tests/            kiểm thử (pytest)
data/raw/casas/   dữ liệu CASAS (tải từ Zenodo, không đưa lên git)
results/          kết quả thực nghiệm (CSV, JSON)
thesis/           mã nguồn LaTeX của khóa luận (thư mục làm việc)
slides/           mã nguồn HTML của slide (xuất PDF bằng trình duyệt)
```

Mỗi đợt làm việc có **một thư mục bàn giao** `v1/`, `v2/`, `v3/`…

## Tài liệu tham khảo chính

- D. Chen. *Sensor-based Human Activity Recognition in a Multi-resident Smart Home Environment.* PhD thesis, AUT, 2021.
- D. J. Cook et al. *CASAS: A Smart Home in a Box.* IEEE Computer, 2013.
- T. Wang, D. J. Cook. *sMRT: Multi-Resident Tracking in Smart Homes With Sensor Vectorization.* IEEE TPAMI, 2021.
- A. Karpekov et al. *DISCOVER: Identifying Patterns of Daily Living in Human Activities from Smart Home Data.* arXiv:2503.01733, 2025.
