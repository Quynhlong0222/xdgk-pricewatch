# Backend cào lại dữ liệu

Dashboard GitHub Pages là web tĩnh, nên nút **Cào lại ngay** cần một backend nhỏ để gọi GitHub Actions mà không lộ token.

## Triển khai bằng Vercel

1. Vào Vercel, import repo `Quynhlong0222/xdgk-pricewatch`.
2. Trong phần Environment Variables, thêm:
   - `GITHUB_TOKEN`: fine-grained token có quyền **Actions: Read and write** cho repo này.
   - `GITHUB_REPOSITORY`: `Quynhlong0222/xdgk-pricewatch`
   - `GITHUB_WORKFLOW_FILE`: `cao-gia.yml`
   - `GITHUB_BRANCH`: `main`
   - `ALLOWED_ORIGIN`: `https://quynhlong0222.github.io`
3. Deploy project.
4. Nếu domain Vercel không phải `https://xdgk-pricewatch.vercel.app`, sửa `config.js`:
   - `crawlApiUrl`: `https://domain-vercel-cua-ban/api/run-crawl`
   - `crawlStatusUrl`: `https://domain-vercel-cua-ban/api/crawl-status`

Sau khi deploy xong, nút **Cào lại ngay** trên dashboard sẽ gửi yêu cầu chạy workflow `Cao gia hang ngay`.

## Thêm đối thủ

Sửa file `sources.json`, thêm một object mới vào mảng `sources`.

Các trường cơ bản:

- `name`: tên đối thủ
- `region`: `bac`, `trung`, hoặc `nam`
- `url`: trang cần cào
- `base`: domain gốc
- `me`: luôn là `false` với đối thủ
- `enabled`: `true`

Với đối thủ có sitemap sản phẩm riêng, cần nâng thêm parser tương ứng trong `crawl.py`.
