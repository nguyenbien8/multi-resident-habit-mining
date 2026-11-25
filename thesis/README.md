# Khóa luận (LaTeX) — mã nguồn văn bản

Đây là thư mục **làm việc**. Bản bàn giao của mỗi đợt nằm ở `vN/khoa_luan_vN_overleaf.zip`.

## Biên dịch trên Overleaf

1. Overleaf: **New Project → Upload Project** → chọn tệp `.zip` trong thư mục `vN/`.
2. **Menu → Settings**: Compiler = **pdfLaTeX**, Main document = `main.tex`.
3. Bấm **Recompile** (Overleaf tự chạy BibTeX cho tài liệu tham khảo).

| Tệp / thư mục | Nội dung |
|---|---|
| `main.tex` | Tệp chính |
| `frontmatter/` | Bìa, lời cảm ơn, lời cam đoan, tóm tắt, từ viết tắt |
| `chapters/` | Chương 1–5 và phụ lục |
| `figures/`, `tables/` | **Tự sinh** bằng `python -m mrhabits.cli figures`; không sửa tay |
| `references.bib` | Tài liệu tham khảo |

Logo trường có sẵn ở `figures/uet_logo.png`, dùng trên bìa (`frontmatter/cover.tex`).
