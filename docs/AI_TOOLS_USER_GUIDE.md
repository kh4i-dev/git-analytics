# Hướng Dẫn Sử Dụng Các Công Cụ AI — Git Analytics

Chào mừng bạn đến với hướng dẫn sử dụng các tính năng AI của **Git Analytics**. Hệ thống tích hợp các mô hình ngôn ngữ lớn (LLM) tiên tiến giúp tăng tốc quy trình làm việc của đội ngũ kỹ thuật thông qua ba công cụ chính: viết commit message, đánh giá Pull Request (PR) diff và trợ lý hỏi đáp về repository.

---

## 1. Giới thiệu Trang AI Tools

Trang **AI Tools** là trung tâm tương tác của bạn với các tính năng trí tuệ nhân tạo trên hệ thống. 

### Cách mở trang AI Tools:
1. Đăng nhập vào ứng dụng **Git Analytics** qua tài khoản GitHub của bạn.
2. Trên thanh menu điều hướng bên trái (Sidebar), nhấn chọn **AI Tools**.
3. Tại đây bạn sẽ thấy giao diện **Trợ lý kỹ thuật** bao gồm 3 phân khu chức năng:
   - Gợi ý commit message
   - Rà soát PR diff
   - Hỏi về codebase (Repo Assistant)

---

## 2. Cách đọc Nhãn Badge Nhà Cung Cấp (Provider Badge)

Ở thanh tiêu đề của trang **AI Workspace**, bạn sẽ thấy một thanh trạng thái hiển thị chính xác nguồn cung cấp AI đang hoạt động:

| Nhãn Badge | Ý nghĩa nguồn/nhà cung cấp hoạt động |
|---|---|
| `<span class="mode-badge enabled">Configured</span>` | Tính năng AI đã được cấu hình thành công và sẵn sàng sử dụng. |
| `<span class="mode-badge disabled">Needs setup</span>` | AI chưa được cấu hình. Bạn cần vào phần Settings để thiết lập khóa BYOK hoặc kích hoạt Cloud AI. |
| **`BYOK · Gemini`** | Bạn đang sử dụng API Key cá nhân (**B**ring **Y**our **O**wn **K**ey) của dịch vụ Google Gemini. |
| **`BYOK · OpenAI`** | Bạn đang sử dụng API Key cá nhân của OpenAI (GPT-4o/GPT-3.5). |
| **`BYOK · Claude`** | Bạn đang sử dụng API Key cá nhân của Anthropic Claude. |
| **`Cloud AI · OpenClaw`** | Hệ thống sử dụng cấu hình Cloud AI của máy chủ, định tuyến qua cổng dịch vụ thông minh OpenClaw gateway. |
| **`Cloud AI · OpenAI-compatible`** | Hệ thống sử dụng cấu hình Cloud AI của máy chủ, định tuyến qua một cổng API tương thích chuẩn OpenAI. |
| **`Cloud AI · [Tên Provider]`** | Hệ thống đang sử dụng cấu hình Cloud AI được thiết lập sẵn bởi Admin phía Server (ví dụ: Cloud AI · Gemini, Cloud AI · OpenAI, Cloud AI · Claude). |

---

## 3. Công cụ 1: Gợi ý Commit Message

Công cụ này giúp bạn tự động viết các thông điệp commit chuẩn hóa theo quy chuẩn **Conventional Commits** từ mã nguồn thay đổi (git diff).

### Bước 1: Cách lấy mã Git Diff sạch từ Terminal của bạn
Bạn có thể chạy các lệnh sau trong thư mục dự án của mình để lấy mã thay đổi:

- **Lấy thay đổi chưa stage (chưa git add):**
  ```bash
  git diff
  ```
- **Lấy thay đổi đã stage (đã chạy git add):**
  ```bash
  git diff --cached
  ```
- **Lấy thay đổi của commit gần nhất (HEAD):**
  ```bash
  git show --format= --patch HEAD
  ```

### Bước 2: Dán mã Diff vào giao diện Web
1. Sao chép toàn bộ nội dung mã diff trả về từ terminal.
2. Dán vào khung văn bản **"Dán git diff vào đây..."** trong mục **Gợi ý commit message**.
3. Nhấn nút **Tạo**.

### Bước 3: Đọc kết quả đầu ra chuẩn
Mô hình sẽ phân tích các dòng code được thêm (`+`) và bớt (`-`) để sinh ra thông điệp Conventional Commit ngắn gọn, tối đa 240 ký tự. Ví dụ đầu ra chuẩn:
```text
feat(analytics): add branch-aware dashboard filters
```
*Mẹo: Bạn có thể chỉnh sửa lại commit message này trực tiếp trên terminal trước khi commit chính thức.*

---

## 4. Công cụ 2: Rà soát Pull Request (PR) Diff

Giúp lập trình viên rà soát nhanh mã nguồn thay đổi trước khi tạo PR hoặc trong quá trình review code chéo để phát hiện lỗi sớm.

### Cách thực hiện:
1. Lấy mã diff của các nhánh bằng cách so sánh nhánh làm việc với nhánh chính (ví dụ: `main`):
   ```bash
   git diff main...ten-nhanh-cua-ban
   ```
2. Dán nội dung diff vào khung nhập của mục **Rà soát PR diff**.
3. Nhấn nút **Review**.

### Kết quả nhận được:
Hệ thống sẽ hiển thị đánh giá dưới dạng văn bản ngắn gọn, tập trung vào:
- **Độ chính xác & Logic:** Phát hiện lỗi logic, rò rỉ bộ nhớ hoặc vòng lặp vô hạn.
- **Bảo mật:** Cảnh báo nếu vô tình để lộ mật khẩu, API key, hoặc sử dụng thư viện kém an toàn.
- **Hiệu năng:** Đề xuất cải tiến thuật toán, giảm truy vấn database không cần thiết.
- **Thiếu kiểm thử:** Gợi ý viết thêm Unit Test cho các trường hợp biên.

---

## 5. Công cụ 3: Trợ lý Hỏi Đáp Codebase (Repo Assistant)

Hỏi đáp tự nhiên về cấu trúc mã nguồn, quy trình nghiệp vụ hoặc hướng dẫn phát triển dựa trên ngữ cảnh dữ liệu repository đã đồng bộ.

### Một số câu hỏi mẫu nên hỏi:
- *"Quy trình xử lý authentication và đăng nhập bằng GitHub hoạt động như thế nào trong project này?"*
- *"Kiến trúc đồng bộ repository (Sync Service) đi qua các service và repository nào?"*
- *"Đề xuất bộ test case cho chức năng chuyển đổi giữa cấu hình BYOK và Cloud AI."*

### Cách gửi câu hỏi:
1. Nhập câu hỏi bằng tiếng Việt hoặc tiếng Anh vào khung nhập của **Repo Assistant**.
2. Nhấn nút **Gửi**.
3. Trợ lý sẽ phân tích mã nguồn và trả lời một cách mạch lạc kèm theo các gợi ý cấu trúc thư mục/tên file liên quan.

---

## 6. Giới hạn & Định dạng Đầu vào Bắt buộc

Để đảm bảo hiệu năng và tính chính xác cao nhất, vui lòng lưu ý các giới hạn thiết kế sau:

- **Định dạng Git Diff bắt buộc:** Khung nhập của Commit Message và PR Review **bắt buộc** phải có định dạng Git Diff tiêu chuẩn. Nội dung nhập phải chứa ít nhất một trong các dòng định danh sau:
  - `diff --git `
  - `--- a/`
  - `+++ b/`
  - `@@ -`
  *Nếu bạn dán văn bản tự do không đúng định dạng diff, hệ thống sẽ báo lỗi `Invalid git diff format provided.` ngay tại giao diện mà không gửi yêu cầu đi.*
- **Giới hạn số lượng ký tự tối đa:** Văn bản đầu vào không được vượt quá số lượng ký tự tối đa quy định bởi máy chủ (mặc định cấu hình hệ thống là 60,000 ký tự). Nếu mã diff quá lớn, bạn nên review từng phần nhỏ hơn.
- **Tránh dán mã nhị phân:** Hãy lọc bỏ các file ảnh hoặc file nhị phân lớn ra khỏi mã diff trước khi dán để giảm tải dung lượng xử lý.
