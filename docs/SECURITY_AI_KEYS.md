# Hướng Dẫn Bảo Mật API Keys — Git Analytics

Bảo vệ API Key là ưu tiên bảo mật hàng đầu của **Git Analytics**. Các khóa truy cập dịch vụ AI (OpenAI, Gemini, Claude) tương đương với tài chính và tài sản số của bạn hoặc của doanh nghiệp. Tài liệu này mô tả chi tiết kiến trúc bảo mật khóa AI của ứng dụng và đưa ra hướng dẫn vận hành an toàn.

---

## 1. Kiến Trúc Lưu Trữ Khóa AI Bảo Mật

Ứng dụng **Git Analytics** được thiết kế dựa trên nguyên tắc **Secret Locality (Bí mật lưu trú cục bộ tại máy chủ)**.

```
[Trình duyệt] ──(Dán API Key thô)──> [FastAPI Server (Mã hóa Fernet)] ──> [Database (Chỉ lưu khóa mã hóa)]
```

### Tại sao không lưu khóa thô trong `localStorage` hoặc `Cookies` của trình duyệt?
- **Nguy cơ tấn công XSS (Cross-Site Scripting)**: Nếu kẻ tấn công chèn được một đoạn mã độc JavaScript vào trang web, toàn bộ dữ liệu lưu trữ tại `localStorage` hoặc `sessionStorage` của trình duyệt sẽ bị đọc và đánh cắp dễ dàng.
- **Rủi ro rò rỉ Client-side**: Việc lưu khóa thô tại client khiến chúng dễ bị lộ thông qua các công cụ phát triển (DevTools), lịch sử trình duyệt hoặc khi chia sẻ thiết bị.

### Giải pháp mã hóa cơ sở dữ liệu phía máy chủ (Server-side Encrypted Storage)
1. Khi người dùng nhập API Key trên giao diện **Settings**, khóa thô sẽ được gửi trực tiếp lên backend thông qua kênh truyền mã hóa HTTPS an toàn.
2. Tại backend, lớp dịch vụ `AiSettingsService` sử dụng thư viện mật mã học tiêu chuẩn để mã hóa đối xứng khóa thô bằng thuật toán **Fernet** (một chuẩn mã hóa bảo mật cao dựa trên AES-128 ở chế độ CBC và xác thực thông tin bằng HMAC-SHA256).
3. Khóa mã hóa (chỉ máy chủ web có thể giải mã nhờ cấu hình `ENCRYPTION_KEY` bí mật) được lưu trữ vào trường `encrypted_api_key` của bảng `ai_settings` trong cơ sở dữ liệu SQLite/PostgreSQL.
4. **Không bao giờ trả lại khóa thô cho Client**: API lấy cấu hình cài đặt (`/api/v1/settings`) chỉ trả về trạng thái `"has_key": true` và nhãn mặt nạ `"masked_key": "********"`. Tuyệt đối không bao giờ trả về chuỗi API Key thô ban đầu.

---

## 2. Chu Kỳ Sống & Quản Lý Khóa BYOK (BYOK Key Lifecycle)

Để quản lý rủi ro tốt nhất, hãy tuân thủ quy trình vòng đời khóa sau đây:

```
[Khởi tạo Khóa với Least Privilege] ──> [Nhập & Mã hóa] ──> [Sử dụng Tạm thời] ──> [Thu hồi & Xóa sạch]
```

- **Quyền hạn tối thiểu (Least Privilege)**: Khi tạo API Key trên Google AI Studio hoặc OpenAI Console, hãy giới hạn quyền hạn của khóa đó. Chỉ cấp quyền đọc/ghi cho mô hình Chat/Completions, không cấp quyền quản lý tài khoản, thay đổi gói thanh toán hoặc cấu hình dự án.
- **Thu hồi khóa nhanh chóng (Revocation)**: Bất cứ khi nào bạn nghi ngờ khóa bị lộ hoặc không còn sử dụng dịch vụ trên Git Analytics nữa, hãy:
  1. Nhấn nút **Delete Key** hoặc **Delete All BYOK Keys** trên giao diện Settings để xóa sạch bản ghi đã mã hóa trong DB.
  2. Truy cập trực tiếp vào trang quản lý của nhà cung cấp AI để tiến hành **Revoke (Hủy bỏ)** hoàn toàn API Key đó. Điều này đảm bảo khóa bị vô hiệu hóa 100% trên toàn cầu.

---

## 3. Quy Tắc Bảo Mật Cho Quản Trị Viên Máy Chủ (Server Administrator Rules)

Nếu bạn chịu trách nhiệm triển khai (deploy) máy chủ **Git Analytics**:

- **Sử dụng `.gitignore` chặt chẽ**: Hãy luôn kiểm tra xem file `.gitignore` đã có dòng cấu hình chặn tệp `.env` hay chưa. Tuyệt đối không bao giờ commit file `.env` chứa API Key Cloud (`OPENAI_API_KEY`, v.v.) lên các repository công khai trên GitHub.
- **Không bao giờ ghi log API Key**: Khi phát triển hoặc sửa đổi mã nguồn, tuyệt đối không sử dụng các lệnh print hoặc logging in ra đối tượng cấu hình hoặc in trực tiếp API Key.
- **Cấu hình `ENCRYPTION_KEY` mạnh mẽ**: Khóa mật mã học này phải là một chuỗi 32-byte an toàn được sinh ra bằng mật mã ngẫu nhiên. Hãy tạo nó bằng lệnh:
  ```bash
  python -c "from app.core.security import generate_encryption_key; print(generate_encryption_key())"
  ```
  Và lưu trữ nó an toàn trong môi trường máy chủ production.

---

## 4. Chụp Ảnh Giao Diện An Toàn (Safe Screenshots)

Khi chia sẻ hình ảnh giao diện báo cáo kỹ thuật hoặc màn hình làm việc của dự án cho người khác hoặc viết tài liệu hướng dẫn:
- **Tuyệt đối không chụp lại màn hình khi đang nhập API Key thô.**
- Badge trạng thái hoạt động (ví dụ: `BYOK · Gemini`) là nhãn hiển thị an toàn vì nó hoàn toàn không chứa bất kỳ thông tin nhạy cảm hay một phần ký tự nào của khóa gốc. Bạn có thể chụp và chia sẻ thoải mái.

---

## 5. Checklist Bảo Mật Trước Khi Lên Production (Production Checklist)

Trước khi cấu hình chạy chính thức hệ thống Git Analytics cho đội ngũ kỹ thuật của bạn, hãy tích vào danh sách kiểm tra sau:

- [ ] **HTTPS**: Đã bật chứng chỉ SSL/TLS trên server để bảo vệ dữ liệu truyền tải giữa Client và Server.
- [ ] **ENCRYPTION_KEY**: Đã thay đổi khóa mã hóa mặc định sang khóa sinh ngẫu nhiên mạnh mẽ phía server.
- [ ] **SECRET_KEY**: Đã cấu hình khóa ký session an toàn trong `.env`, không dùng giá trị mặc định `change-me-in-local-env`.
- [ ] **Least Privilege keys**: Các khóa API Cloud hoặc BYOK chỉ được phân quyền tối thiểu cần thiết.
- [ ] **Rate Limiting**: Biến `CLOUD_AI_PREVIEW_DAILY_LIMIT` được cấu hình hợp lý để bảo vệ máy chủ khỏi nguy cơ spam hóa đơn tài chính AI.
- [ ] **Database Backup Access**: Quyền truy cập vào file cơ sở dữ liệu SQLite (`git_analytics.db`) hoặc Server PostgreSQL được giới hạn chặt chẽ, chỉ cho phép process của ứng dụng truy cập.
