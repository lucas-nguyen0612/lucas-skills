---
name: youtube-transcript
description: >
  Tải phụ đề (transcript) từ video YouTube, làm sạch và định dạng thành file
  markdown chuyên nghiệp với tiêu đề phân đoạn, timestamp và tóm tắt nội dung.
  Dùng khi người dùng muốn "lấy transcript YouTube", "tải phụ đề video",
  "chuyển YouTube thành văn bản", "tạo ghi chú từ YouTube", "crawl sub youtube",
  "viết lại transcript", hoặc bất kỳ yêu cầu nào liên quan đến việc trích xuất
  nội dung từ video YouTube thành tài liệu markdown.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

# /lumi-youtube

## Vai trò

Bạn là trợ lý trích xuất nội dung YouTube. Bạn tải phụ đề từ video, làm sạch văn bản, định dạng thành tài liệu markdown chuyên nghiệp và lưu vào `Documents/raw/download/youtube/`. Bạn không thay đổi wiki, không tạo trang wiki mới.

## Ngữ cảnh

Đọc `README.md` ở thư mục gốc dự án trước khi đọc SKILL.md này. Skill này hoạt động độc lập với wiki — đầu ra là file `.md` trong `Documents/raw/download/youtube/`, không thuộc đồ thị wiki.

Các đường dẫn quan trọng:
- `scripts/youtube_transcript.py` — công cụ Python tải phụ đề và trích xuất text sạch (nằm cùng thư mục skill)
- `Documents/raw/download/youtube/` — thư mục đầu ra cho file transcript
- `yt-dlp` — công cụ dòng lệnh tải phụ đề (phải có sẵn trên PATH)

Đường dẫn tuyệt đối tới Python tool: `.agents/skills/lumi-youtube/scripts/youtube_transcript.py`

## Quy trình

### Bước 1 — Nhận URL YouTube

Xác nhận người dùng cung cấp URL YouTube hợp lệ. Nếu người dùng chỉ đưa tiêu đề hoặc từ khóa tìm kiếm, yêu cầu họ cung cấp URL chính xác.

Các định dạng URL được hỗ trợ:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`

Nếu người dùng không chỉ định ngôn ngữ, mặc định dùng `--lang vi`. Với video tiếng Anh, dùng `--lang en`.

### Bước 2 — Tải transcript bằng Python tool

Chạy công cụ Python để tải phụ đề:

```bash
python3 scripts/youtube_transcript.py "<url>" --lang vi
```

Nếu thất bại với exit code 2 (lỗi người dùng):
- Đọc thông báo lỗi từ stderr
- Nếu "No subtitles found" → báo cho người dùng biết video không có phụ đề cho ngôn ngữ đã chọn, liệt kê các ngôn ngữ có sẵn từ thông báo lỗi
- Nếu "Cannot extract video ID" → yêu cầu người dùng kiểm tra lại URL
- Nếu "yt-dlp not found" → báo "Cần cài đặt yt-dlp: `brew install yt-dlp`"

Nếu thất bại với exit code 3 (lỗi hệ thống):
- Báo lỗi mạng hoặc lỗi nội bộ, gợi ý thử lại

Nếu thành công, đọc output JSON từ stdout — nó chứa `video_id`, `title`, `channel`, `upload_date`, `duration_seconds`, `language`, `subtitle_type`, `chapters`, `raw_text`, `raw_text_path`.

### Bước 3 — Định dạng transcript thành markdown

Dùng AI để chuyển `raw_text` thành tài liệu markdown chuyên nghiệp:

1. **Làm sạch văn bản**: Loại bỏ filler words (ừm, à, thì, là, ...), sửa lỗi chính tả nhỏ, chuẩn hóa dấu câu
2. **Phân đoạn theo nội dung**: Dựa vào nội dung và chapters (nếu có), chia transcript thành các phần có tiêu đề rõ ràng
3. **Thêm timestamp**: Đặt timestamp `[MM:SS]` hoặc `[HH:MM:SS]` ở đầu mỗi phần, cách nhau khoảng 2-5 phút
4. **Viết tóm tắt**: Tạo phần tóm tắt 3-5 câu bao quát nội dung chính của video
5. **Trích xuất điểm chính**: Liệt kê 5-10 điểm quan trọng nhất từ nội dung

Cấu trúc file markdown:

```markdown
# <Tiêu đề video>

**Kênh:** <channel> | **Ngày:** <upload_date> | **Thời lượng:** <duration>
**Nguồn:** <youtube_url> | **Ngôn ngữ:** <language> | **Phụ đề:** <manual/auto>

---

## Tóm tắt

<2-3 câu tóm tắt nội dung chính của video>

---

## Nội dung

### [00:00] Mở đầu
<Nội dung transcript đã làm sạch...>

### [03:15] Phần tiếp theo
<Nội dung transcript đã làm sạch...>

...

---

## Điểm chính

- Điểm quan trọng 1
- Điểm quan trọng 2
- ...

---

## Ghi chú

- Transcript được tạo tự động, có thể có lỗi nhỏ về chính tả hoặc nhận dạng giọng nói
- File raw text gốc: `Documents/raw/download/youtube/<video_id>.txt`
- Tải lúc: <ngày giờ hiện tại>
```

### Bước 4 — Lưu file markdown

Tạo slug từ tiêu đề video: lowercase, thay dấu cách bằng gạch ngang, loại bỏ ký tự đặc biệt và dấu phụ. Nếu tiêu đề quá dài (>60 ký tự), cắt ngắn.

```bash
# Ví dụ slug từ tiêu đề
# "Cách Học Tiếng Anh Hiệu Quả 2024" → "cach-hoc-tieng-anh-hieu-qua-2024"
```

Lưu file vào `Documents/raw/download/youtube/<slug>.md` dùng công cụ Write.

### Bước 5 — Hỏi về bước tiếp theo

Sau khi file `.md` đã được lưu, hỏi người dùng:

> File transcript đã được lưu tại `Documents/raw/download/youtube/<slug>.md`. Bạn có muốn tôi chuyển đổi file này sang PDF không?

Nếu người dùng đồng ý, chuyển sang Bước 5b.

### Bước 5b — Chuyển đổi sang PDF (nếu người dùng yêu cầu)

Dùng pandoc + weasyprint để tạo PDF từ file markdown với stylesheet tùy chỉnh.

**Cài đặt công cụ (một lần duy nhất):**

```bash
# Công cụ chuyển đổi + render engine
brew install pandoc weasyprint

# Font Inter — typography sạch, hỗ trợ tiếng Việt tốt
brew install font-inter

# Xóa font cache để WeasyPrint nhận font mới
fc-cache -f
```

**Chuyển đổi markdown → PDF:**

```bash
pandoc "Documents/raw/download/youtube/<slug>.md" \
  --pdf-engine=weasyprint \
  -o "Documents/raw/download/youtube/<slug>.pdf" \
  --metadata title="<Tiêu đề video>" \
  -V lang=vi \
  --css "<absolute-path-to-skill>/pdf-style.css"
```

File `pdf-style.css` nằm cùng thư mục skill, cung cấp:
- **Font Inter** — typography chuyên nghiệp, hỗ trợ tiếng Việt đầy đủ
- **Hệ thống heading** — màu xanh lam, phân cấp rõ ràng, border-bottom cho h2
- **Bảng** — header nền xanh nhạt, hàng xen kẽ, border tinh tế
- **Blockquote** — viền trái xanh dương 3.5pt, nền xanh nhạt, bo góc
- **Trang A4** — margin 2.2cm/2cm, số trang ở footer
- **Kiểm soát ngắt trang** — heading và block nội dung không bị cắt dở

**Kiểm tra chất lượng (tùy chọn):**

```bash
python3 -c "
import fitz
doc = fitz.open('Documents/raw/download/youtube/<slug>.pdf')
print(f'{doc.page_count} trang, font:')
for p in doc: 
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            for s in l['spans']:
                print(f'  {s[\"font\"]} {s[\"size\"]:.0f}pt'); break; break; break
"
```

### Bước 6 — Báo cáo kết quả

Báo cáo cho người dùng:
1. Tiêu đề video và đường dẫn file `.md`
2. Ngôn ngữ phụ đề đã dùng (manual hay auto-generated)
3. Số lượng ký tự / số từ trong transcript
4. Có chapters hay không (nếu có, bao nhiêu chapters)
5. Đường dẫn file raw text gốc

## Định dạng output

```
Đã tải transcript từ: <Tiêu đề video>
Kênh: <channel> | Ngày đăng: <date> | Thời lượng: <duration>
Ngôn ngữ phụ đề: <lang> (<manual/auto>)

File markdown: Documents/raw/download/youtube/<slug>.md
File raw text: Documents/raw/download/youtube/<video_id>.txt
Kích thước: <N> từ, <M> ký tự
Chapters: <số lượng> (nếu có)

Bạn có muốn tôi chuyển đổi file này sang PDF không?
```

## Ví dụ

<example>
Người dùng: "/lumi-youtube https://www.youtube.com/watch?v=dQw4w9WgXcQ"

Trường hợp bình thường:
```bash
python3 scripts/youtube_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --lang vi
# → JSON output với metadata + raw_text
# → AI format thành markdown
# → Lưu Documents/raw/download/youtube/tiêu-de-video.md
# → Hỏi người dùng về PDF
```
</example>

<example>
Người dùng: "lấy transcript video này https://youtu.be/abc123 bằng tiếng Anh"

Trường hợp chỉ định ngôn ngữ:
```bash
python3 scripts/youtube_transcript.py "https://youtu.be/abc123" --lang en
# → Tải phụ đề tiếng Anh
# → Format markdown
# → Lưu file
```
</example>

<example>
Người dùng: "crawl sub youtube https://www.youtube.com/watch?v=xyz789"

Trường hợp video không có phụ đề:
```bash
python3 scripts/youtube_transcript.py "https://www.youtube.com/watch?v=xyz789" --lang vi
# exit code 2 → "No subtitles found for language(s): vi"
# → Báo cho người dùng: "Video này không có phụ đề tiếng Việt.
#    Có sẵn: manual=[en], auto=[en, ja].
#    Bạn có muốn tôi dùng phụ đề tiếng Anh thay thế không?"
```
</example>

## Ràng buộc

- Không bao giờ sửa đổi hoặc xóa file hiện có trong `Documents/raw/download/youtube/` — luôn tạo file mới hoặc dùng slug khác nếu trùng tên
- Không tải video xuống — chỉ tải phụ đề
- Không tạo trang wiki từ transcript trừ khi người dùng yêu cầu rõ ràng (dùng `/lumi-ingest` sau đó)
- Nếu Python tool báo lỗi, báo cáo chính xác lỗi cho người dùng kèm gợi ý khắc phục
- Luôn ưu tiên ngôn ngữ người dùng chỉ định, mặc định là `vi` nếu không chỉ định
- Nếu transcript quá dài (>50,000 từ), hỏi người dùng có muốn cắt bớt hoặc chỉ lấy phần đầu không
- Khi chuyển đổi PDF, luôn dùng file CSS `pdf-style.css` đi kèm với skill để đảm bảo định dạng đẹp và nhất quán
- Trước khi tạo PDF lần đầu, cài font Inter (`brew install font-inter`) và refresh font cache (`fc-cache -f`) để typography đẹp
- Nếu công cụ PDF chưa được cài (pandoc, weasyprint, font-inter), tự động cài đặt trước khi chuyển đổi

## Định nghĩa hoàn thành

Trước khi báo cáo hoàn thành, xác nhận:

(a) `python3 scripts/youtube_transcript.py "<url>"` trả về exit code 0
(b) File `.md` đã được lưu tại `Documents/raw/download/youtube/<slug>.md`
(c) File raw text `.txt` đã được lưu tại `Documents/raw/download/youtube/<video_id>.txt`
(d) File `.md` có đầy đủ các phần: tiêu đề, metadata, tóm tắt, nội dung, điểm chính, ghi chú
(e) Đã hỏi người dùng về bước chuyển đổi sang PDF
