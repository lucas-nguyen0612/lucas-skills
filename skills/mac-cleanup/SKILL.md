---
name: mac-cleanup
description: >
  Định kỳ dọn dung lượng Mac của Lucas: quét CHỈ ĐỌC tìm cache dev, build còn sót
  của dự án đã xong, Docker image/volume không dùng, model AI cũ, file trùng; vẽ
  "Bản đồ dung lượng Mac" (artifact có treemap + checklist để tick), rồi chỉ xoá
  đúng các mục người dùng chọn bằng script có dry-run. Dùng khi người dùng gõ
  /mac-cleanup hoặc nói "dọn máy", "Mac đầy", "hết dung lượng", "giải phóng ổ
  cứng", "dọn dẹp lại máy", "disk full", "clean up my Mac", hoặc dán dòng
  "Dọn các mục: ..." / "Dọn tiếp các mục: ..." copy từ bản đồ.
argument-hint: "[quét | Dọn các mục: id1, id2, ...]"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Artifact
---

# Dọn dung lượng Mac

Giao tiếp bằng tiếng Việt. Nguyên tắc số 1: **không xoá gì khi người dùng chưa tick chọn.**
Bước quét chỉ đọc; bước xoá chỉ chạm vào đúng các mục có trong dòng "Dọn các mục: …".

Trạng thái lưu ở `~/.claude/mac-cleanup.json`:
- `artifact_url`: link bản đồ. Luôn cập nhật artifact này (giữ nguyên link), không tạo link mới.
- `history`: mỗi lần dọn một dòng (ngày, trống trước/sau, GB đã gỡ, số mục).

## Chọn chế độ

- Người dùng dán `Dọn các mục: …` hoặc `Dọn tiếp các mục: …` → nhảy tới **Bước 3**.
- Còn lại (kể cả chỉ nói "dọn máy") → **Bước 1**.

## Bước 1: Quét chỉ đọc

```bash
zsh ~/.claude/skills/mac-cleanup/scripts/scan.sh <scratchpad>/scan
```

Đọc `overview.txt`, `build-dirs.tsv`, `dups.txt`, `documents-access`. Đào sâu thêm bằng
`du`/`ls` nếu một mục to bất thường. Với mỗi mục định đề xuất, kiểm tra trước khi xếp loại:

| Loại | Cách kiểm |
|---|---|
| Docker image/volume | Chỉ đề xuất cái không container nào dùng (`docker ps -a`, `docker system df -v`). Volume Supabase của dự án đã dừng = mất DB local → "Cân nhắc". |
| Build dự án (`node_modules`, `.next`, `.venv`…) | Xem ngày sửa cuối (`stat -f %Sm`). Dự án lâu không đụng → an toàn, cài lại được. |
| Node trong nvm | Không đề xuất bản `default`. Liệt kê gói global sẽ mất theo. |
| Model HuggingFace/Whisper | Ghi rõ tên model, tải lại được nhưng tốn thời gian → "Cân nhắc" nếu còn dùng gần đây. |
| File trùng (`dups.txt`) | Chỉ trùng md5 thật. Giữ bản gốc (tên không có hậu tố ` 1`, ` 2`), chuyển bản kia vào Thùng rác. |
| Cache (npm, uv, pnpm, Chrome, JetBrains, Codex, go-build…) | An toàn. Với pnpm dùng `pnpm store prune` (chỉ gỡ gói không còn dự án nào tham chiếu). |
| App đang mở (Claude Desktop, JetBrains, Docker) | Kiểm `pgrep`; nếu đang chạy thì ghi chú cần tắt app trước khi xoá cache/VM của nó. |

Không bao giờ đề xuất: `~/Documents`, `~/Desktop`, ảnh/video gốc, `~/.ssh`, keychain, `.git`,
`~/.claude` (trừ khi người dùng hỏi), dữ liệu app không phải cache, file hệ thống ngoài home.

Mỗi mục có: `id` (kebab-case, ổn định giữa các lần), nhóm, tên, dung lượng GB, mức
`safe` (an toàn, tự tạo lại) hoặc `consider` (mất dữ liệu cục bộ), lệnh/đường dẫn sẽ xoá,
một câu giải thích.

## Bước 2: Vẽ bản đồ

Đọc artifact hiện có (`Artifact action:read` với `artifact_url`) và giữ nguyên thiết kế:
thanh dung lượng ổ, treemap (ô tỉ lệ dung lượng, bấm để tick), checklist theo nhóm, nút
"Chọn mọi mục an toàn", log "Đã dọn", ghi chú, thanh dưới cùng có nút **Sao chép lựa chọn**
xuất ra đúng chuỗi `Dọn các mục: id1, id2, …`. Chỉ thay mảng dữ liệu `ITEMS`, `KEEP`,
`DONE`, các số liệu tóm tắt, ngày cập nhật và ghi chú. Đổi khoá `localStorage` (vd `sel-<ngày>`)
để lựa chọn cũ không dính sang lần quét mới. Lưu file vào scratchpad rồi publish với `url`
= `artifact_url`. Nếu không có artifact cũ (hoặc bị xoá), tạo mới theo cùng cấu trúc (nạp
skill `artifact-design` trước) và ghi URL mới vào `mac-cleanup.json`.

Trả lời ngắn trong terminal: trống hiện tại, tổng có thể dọn (an toàn / cân nhắc), 3 mục
lớn nhất, link bản đồ. Rồi dừng, chờ người dùng tick.

## Bước 3: Dọn theo lựa chọn

1. Map từng `id` sang lệnh từ lần quét gần nhất (nếu không còn trong context, đọc mảng
   `ITEMS` trong artifact). `id` không nhận ra → hỏi lại, không đoán.
2. Viết `<scratchpad>/don-dep.sh` (zsh) có cờ `--dry-run`. Mỗi mục: kiểm đường dẫn tồn tại,
   in dung lượng trước, xoá, in "✓ id". Ưu tiên lệnh của công cụ (`docker image prune`,
   `docker volume rm`, `npm cache clean --force`, `uv cache clean`, `pnpm store prune`,
   `go clean -modcache`, `nvm uninstall`) hơn `rm -rf`. File trùng và file người dùng →
   chuyển vào `~/.Trash` thay vì xoá hẳn. Dùng `set -u`, quote mọi đường dẫn, không dùng
   biến rỗng trong `rm -rf`.
3. Chạy `--dry-run`, cho người dùng xem tóm tắt. Nếu có mục `consider`, nhắc lại rõ dữ
   liệu gì sẽ mất và chờ "ok". Mục toàn `safe` thì chạy luôn.
4. Chạy thật, rồi đo lại `df -h /System/Volumes/Data` và `du` các mục vừa dọn.
5. Cập nhật artifact: chuyển mục đã dọn sang `DONE` (ghi ngày), bỏ khỏi `ITEMS`, cập nhật
   số liệu. Thêm một dòng vào `history` trong `mac-cleanup.json`.
6. Báo: đã gỡ bao nhiêu GB, trống còn bao nhiêu, mục nào lỗi/bỏ qua và lý do.

## Những điều đã biết về máy này

- **`~/Documents` bị macOS (TCC) chặn** với Claude Code dù Terminal có Full Disk Access.
  Khi `documents-access` = `blocked`, đừng mất thời gian debug quyền: viết
  `~/quet-documents.sh` (chỉ đọc, ghi kết quả ra `~/quet-documents.txt`) để người dùng tự
  chạy trong tab Terminal mới, rồi đọc file kết quả. Dự án Vtech nằm ở `~/Documents/Vtech`.
- **Swap** (`sysctl vm.swapusage`) có thể chiếm 10 GB+ và làm số trống tụt sau khi dọn. Ghi
  chú cho người dùng; nó tự trả khi tắt Docker/trình duyệt hoặc khởi động lại.
- **Docker.raw** không co lại ngay sau khi prune; đo bằng `du -h` (dung lượng thật), không
  dùng `ls -l`.
- **npm/npx cache** đầy lại ~1,5 GB sau một ngày: bình thường, chỉ đề xuất khi > 5 GB.
- **pnpm store** phần lớn vẫn được dự án tham chiếu; prune chỉ gỡ phần thừa.
- Node mặc định là v24 (kiểm lại `~/.nvm/alias/default` mỗi lần).
- Lần dọn đầu (18/10/2026): từ 47 GB trống lên ~149 GB. Mục lớn nhất là Docker image,
  uv cache, npm cache, Thùng rác, VM Claude Desktop, model HuggingFace.
