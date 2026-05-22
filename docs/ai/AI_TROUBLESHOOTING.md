# Hướng Dẫn Khắc Phục Sự Cố AI — Git Analytics

Tài liệu này tổng hợp các lỗi thường gặp trong quá trình sử dụng các công cụ AI trên **Git Analytics**, nguyên nhân gốc rễ và các bước xử lý chi tiết để khắc phục sự cố nhanh chóng.

---

## 1. Các Lỗi Giao Diện & Cách Khắc Phục

### ❌ Lỗi 1: Giao diện hiển thị badge trạng thái `Needs setup`
- **Hiện tượng**: Khung hiển thị nhà cung cấp ở trang AI Tools báo `Needs setup` và các nút chức năng bị vô hiệu hóa (disabled).
- **Nguyên nhân**: Người dùng hiện tại chưa bật tính năng AI. Cơ sở dữ liệu chưa ghi nhận API Key BYOK nào và máy chủ cũng không cấu hình Cloud AI hoặc không có key Cloud khả dụng.
- **Cách xử lý**:
  1. Vào menu **Settings** > tab **AI Settings**.
  2. Điền API Key của một trong ba nhà cung cấp (Gemini, OpenAI, Claude) vào mục BYOK và nhấn **Save Settings**.
  3. Nếu bạn là quản trị viên máy chủ và muốn bật Cloud AI, hãy kiểm tra xem file `.env` đã khai báo đầy đủ `OPENAI_API_KEY`, `GEMINI_API_KEY` hay chưa, sau đó khởi động lại server.

---

### ❌ Lỗi 2: Lỗi báo `Invalid git diff format provided` hoặc `diff is required`
- **Hiện tượng**: Khi nhấn nút tạo commit message hoặc review, ứng dụng hiển thị thông báo lỗi màu đỏ `Invalid git diff format provided.` hoặc `diff is required.`
- **Nguyên nhân**: 
  - Khung văn bản đang bị để trống.
  - Văn bản bạn dán vào không phải là Git Diff tiêu chuẩn. Hệ thống yêu cầu mã đầu vào phải chứa các dòng header định danh của git diff như `diff --git `, `--- a/`, `+++ b/`, hoặc `@@ -`.
- **Cách xử lý**:
  1. Mở terminal tại dự án của bạn và chạy lệnh lấy diff chuẩn: `git diff` (hoặc `git diff --cached` nếu đã add thay đổi).
  2. Sao chép và dán toàn bộ kết quả xuất ra (bao gồm cả dòng tiêu đề bắt đầu bằng `diff --git ...`) vào khung nhập của Web UI.

---

### ❌ Lỗi 3: Lỗi báo lỗi khóa API `Invalid API key configured for the AI provider. Please check your key in Settings.` (401/403)
- **Hiện tượng**: Các nút bấm AI báo lỗi xác thực không thành công.
- **Nguyên nhân**: API Key bạn cấu hình trong Settings (đối với BYOK) hoặc cấu hình trong `.env` (đối với Cloud AI) đã hết hạn, bị thu hồi hoặc nhập sai ký tự (thừa khoảng trắng, thiếu ký tự).
- **Cách xử lý**:
  1. Truy cập vào trang quản lý API Key của nhà cung cấp tương ứng (Google AI Studio, OpenAI Console, Anthropic Console) để kiểm tra trạng thái hoạt động của khóa.
  2. Vào **Settings** > **AI Settings** trên Web UI.
  3. Xóa khóa cũ đi và dán lại khóa mới chuẩn xác. Nhấn **Save Settings**.

---

### ❌ Lỗi 4: Lỗi báo vượt quá hạn ngạch `AI provider rate limit exceeded.` hoặc `Cloud AI preview daily limit reached.` (429)
- **Hiện tượng**: Gặp lỗi khi gọi AI và nhận thông báo lỗi liên quan tới rate limit hoặc hạn ngạch sử dụng hàng ngày.
- **Nguyên nhân**:
  - Với **BYOK**: Tài khoản trả phí/miễn phí của cá nhân bạn với nhà cung cấp (OpenAI/Gemini/Claude) đã hết số dư hoặc tần suất gọi quá nhanh trong 1 phút.
  - Với **Cloud AI**: Bạn đã vượt quá giới hạn dùng thử miễn phí trong ngày do quản trị viên máy chủ cấu hình trong `.env` (mặc định là `CLOUD_AI_PREVIEW_DAILY_LIMIT=30` lượt gọi/ngày).
- **Cách xử lý**:
  - Đợi qua ngày hôm sau để reset lượt dùng thử của Cloud AI.
  - Chuyển sang sử dụng chế độ **BYOK** và cung cấp API Key cá nhân của bạn để không bị giới hạn bởi quota dùng thử của máy chủ.
  - Kiểm tra số dư tài khoản của bạn trên nền tảng của nhà cung cấp AI.

---

### ❌ Lỗi 5: Đầu ra của AI bị rỗng (Empty Output)
- **Hiện tượng**: Cuộc gọi báo thành công nhưng kết quả trả về không có nội dung chữ hoặc hiển thị lỗi "AI provider returned no text".
- **Nguyên nhân**: File diff đầu vào chứa thay đổi quá lớn, cấu trúc phức tạp khiến mô hình LLM bị quá tải hoặc mã diff chỉ chứa thay đổi trên file nhị phân (như hình ảnh, file nén).
- **Cách xử lý**:
  - Chia nhỏ các commit của bạn hoặc lọc bớt các file nhị phân lớn ra khỏi diff trước khi dán vào Web UI.

---

## 2. Sự Cố Hiển Thị & Trình Duyệt

### ❌ Hiện tượng 1: Lỗi font tiếng Việt / Hiển thị ký tự lạ (Mojibake)
- **Hiện tượng**: Kết quả trả về của trợ lý AI bị lỗi mã hóa font chữ tiếng Việt.
- **Nguyên nhân**: File cấu hình `.env` hoặc cơ sở dữ liệu SQLite của bạn không sử dụng mã hóa UTF-8.
- **Cách xử lý**:
  - Hãy đảm bảo biến cấu hình trong `.env` được lưu dưới định dạng tệp tin mã hóa `UTF-8`.
  - Khởi động ứng dụng với biến môi trường Python chuẩn: `PYTHONIOENCODING=utf-8`.

### ❌ Hiện tượng 2: Thay đổi cấu hình trong Settings nhưng trang AI Tools vẫn hiển thị Badge cũ
- **Hiện tượng**: Bạn vừa cập nhật Key BYOK mới hoặc chuyển đổi nhà cung cấp nhưng badge ở trang AI Tools không cập nhật.
- **Nguyên nhân**: Trình duyệt lưu cache cục bộ trang web hoặc Session cookie cũ chưa được làm mới.
- **Cách xử lý**:
  1. Nhấn tổ hợp phím `Ctrl + F5` (hoặc `Cmd + Shift + R` trên macOS) để tải lại trang bỏ qua cache.
  2. Đăng xuất ra khỏi hệ thống và thực hiện đăng nhập lại qua OAuth để thiết lập lại Session sạch.

---

## 3. Hướng Dẫn Kiểm Tra Log Máy Chu An Toàn

Khi gặp các lỗi hệ thống không rõ nguyên nhân, bạn có thể kiểm tra tệp tin log của máy chủ FastAPI để điều tra chi tiết.

### Quy tắc bảo mật log tuyệt đối:
> [!WARNING]
> **Không bao giờ in hoặc xuất thông tin API Key thô (raw keys) ra màn hình Console hoặc ghi vào file Log.**
> Tất cả các API Key BYOK khi lưu xuống Database đã được mã hóa Fernet. Khi đọc log, hãy đảm bảo hệ thống logging không sử dụng chế độ in toàn bộ đối tượng config hoặc payload.

### Cách kiểm tra log an toàn:
1. Mở terminal nơi máy chủ FastAPI đang chạy.
2. Kiểm tra các dòng log có mã trạng thái lỗi HTTP hoặc các lỗi Python Exception:
   - Các dòng log báo lỗi `ValidationException` là lỗi đầu vào bình thường do người dùng nhập thiếu/sai định dạng.
   - Các dòng log báo lỗi `AIProviderException` chỉ ra sự cố kết nối giữa máy chủ của bạn với endpoint của OpenAI/Gemini/Claude (ví dụ: mất kết nối internet hoặc API của nhà cung cấp đang bảo trì).
