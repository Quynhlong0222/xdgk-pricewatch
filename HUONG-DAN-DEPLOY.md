# Hướng dẫn đưa dashboard lên mạng (GitHub Pages — miễn phí)

Sau khi làm xong, anh có 1 link dạng `https://TEN-CUA-ANH.github.io/pricewatch/` gửi cho bất kỳ ai xem, và hệ thống **tự cào giá mỗi sáng 5h** không cần máy anh bật. Tổng thời gian làm: ~15 phút, chỉ thao tác trên trình duyệt, không cần cài gì.

## Bước 1 — Tạo tài khoản GitHub (nếu chưa có)

Vào https://github.com/signup, đăng ký bằng email (nên dùng xedapgiakho023@gmail.com). Miễn phí.

## Bước 2 — Tạo repo

1. Vào https://github.com/new
2. Repository name: `pricewatch` (hoặc tên khác tùy anh)
3. Chọn **Public** (bắt buộc để dùng Pages miễn phí)
4. Bấm **Create repository**

## Bước 3 — Đưa 3 file lên

1. Trong trang repo vừa tạo, bấm link **uploading an existing file**
2. Kéo thả 3 file trong folder `github-pages` này vào: `index.html`, `crawl.py`, `gia-lich-su.json`
   (KHÔNG kéo file `cao-gia.yml` và file hướng dẫn này)
3. Bấm **Commit changes**

## Bước 4 — Tạo workflow tự cào

1. Trong repo, bấm **Add file → Create new file**
2. Ô tên file, gõ chính xác: `.github/workflows/cao-gia.yml` (gõ dấu `/` sẽ tự tạo folder)
3. Mở file `cao-gia.yml` trong folder này bằng Notepad/TextEdit, copy toàn bộ nội dung, dán vào
4. Bấm **Commit changes**

## Bước 5 — Bật Pages

1. Vào **Settings** (tab trên cùng của repo) → **Pages** (menu trái)
2. Mục "Build and deployment" → Source: **Deploy from a branch**
3. Branch: chọn **main**, folder **/ (root)** → **Save**
4. Đợi ~2 phút, quay lại trang Pages sẽ hiện link dạng `https://TEN-CUA-ANH.github.io/pricewatch/` — đó là link để share.

## Bước 6 — Chạy thử cào tự động

1. Vào tab **Actions** của repo → nếu hiện nút "I understand my workflows, go ahead and enable them" thì bấm
2. Menu trái chọn **Cao gia hang ngay** → bấm **Run workflow** → **Run workflow**
3. Đợi ~1 phút, chạy xong màu xanh ✓ là được. Từ giờ nó tự chạy 5h sáng mỗi ngày.

## Xong! Vài điều cần biết

- **Ai thấy được link?** Bất kỳ ai có link đều xem được (repo Public). Dữ liệu chỉ là giá bán công khai nên thường không sao. Muốn giới hạn người xem thật sự thì cần Cloudflare Pages + Access (nói với Claude để được hướng dẫn).
- **Thêm/bớt web đối thủ:** mở file `crawl.py` trên GitHub (bấm vào file → icon bút chì), sửa danh sách `SOURCES` ở đầu file. Mỗi nguồn cần: tên, miền (`bac`/`trung`/`nam`), URL trang danh mục. Nhờ Claude thêm giúp cũng được.
- **Đổi giờ cào:** sửa dòng `cron: "0 22 * * *"` trong workflow (22h UTC = 5h sáng VN). Ví dụ cào thêm 13h VN: thêm dòng `- cron: "0 6 * * *"`.
- **Dashboard trong Cowork vẫn dùng được** — bấm "Cào ngay" là có số liệu tức thời trên máy anh; bản online thì tự cập nhật mỗi sáng cho cả team xem.
- Nếu sau này web đối thủ đổi giao diện làm parser hụt sản phẩm, quay lại nói Claude sửa `crawl.py`.
