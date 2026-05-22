# Hướng Dẫn Cấu Hình Hệ Thống AI — Git Analytics

Tài liệu này cung cấp hướng dẫn kỹ thuật chi tiết để cấu hình hệ thống AI trên ứng dụng **Git Analytics**, bao gồm hai chế độ hoạt động chính: **BYOK (Bring Your Own Key)** và **Cloud AI (Cấu hình phía máy chủ)**.

---

## 1. Phân Biệt Các Chế Độ AI Hoạt Động

Ứng dụng hỗ trợ hai cơ chế phân giải nhà cung cấp AI khi xử lý các cuộc gọi từ công cụ:

| Tiêu chí | Chế độ BYOK (Bring Your Own Key) | Chế độ Cloud AI |
|---|---|---|
| **Định nghĩa** | Người dùng tự cung cấp và quản lý API Key của riêng mình. | Ứng dụng sử dụng cấu hình API Key có sẵn tại Server. |
| **Nơi lưu trữ Key** | Lưu trữ mã hóa dưới Database SQLite/PostgreSQL của ứng dụng. | Khai báo trực tiếp trong file `.env` cấu hình của máy chủ. |
| **Quyền kiểm soát** | Người dùng chịu trách nhiệm chi phí và hạn ngạch của khóa cá nhân. | Admin máy chủ cung cấp hạn ngạch chạy thử (mặc định 30 lượt/ngày). |
| **Dịch vụ hỗ trợ** | OpenAI, Google Gemini, Anthropic Claude. | OpenAI, Gemini, Claude hoặc Cổng tương thích OpenAI (OpenClaw). |

### 💡 Lưu ý về Local Runtime và Local AI Mode:
- **Local Runtime (Môi trường chạy cục bộ)**: Nghĩa là máy chủ web Git Analytics đang chạy trực tiếp trên thiết bị của bạn (`localhost:8000`), không phải môi trường cloud production.
- **Local AI Mode (Không áp dụng)**: Ứng dụng **không** chạy mô hình AI trực tiếp cục bộ trên máy tính (như Ollama hay Llama.cpp) mà luôn giao tiếp với các Cloud API của các nhà cung cấp thông qua giao thức HTTPS. Tuy nhiên, dù chạy ứng dụng trên localhost, bạn vẫn hoàn toàn cấu hình được cả hai chế độ **BYOK** và **Cloud AI**.

---

## 2. Cấu Hình Chế Độ BYOK (Bring Your Own Key)

Chế độ BYOK cho phép từng người dùng nhập mã khóa API của riêng họ.

### Cách cấu hình trên Giao diện Web:
1. Đăng nhập vào **Git Analytics**.
2. Nhấp vào ảnh đại diện hoặc menu **Settings** ở thanh điều hướng.
3. Chuyển sang tab **AI Settings**.
4. Chọn nhà cung cấp mặc định (Default Provider) bạn muốn sử dụng (ví dụ: Gemini, OpenAI, Claude).
5. Nhập khóa API tương ứng vào mục **API Keys**:
   - Khóa OpenAI (bắt đầu bằng `sk-...`)
   - Khóa Gemini (lấy từ Google AI Studio)
   - Khóa Claude (lấy từ Anthropic Console)
6. Nhấn nút **Save Settings**.

> [!IMPORTANT]
> **Quy tắc Bảo mật tối quan trọng:** Người dùng tuyệt đối **KHÔNG** được ghi các API Key BYOK cá nhân này vào file cấu hình `.env` của dự án. Giao diện Web của Git Analytics sẽ tự động mã hóa khóa bằng thuật toán đối xứng Fernet (sử dụng `ENCRYPTION_KEY` phía server) trước khi lưu xuống Database SQLite.

---

## 3. Cấu Cấu Hình Chế Độ Cloud AI (Server-side Config)

Chế độ **Cloud AI** được quản trị viên máy chủ cấu hình trực tiếp thông qua các biến môi trường trong file `.env` của Server. Khi được cấu hình, người dùng không cần nhập API Key vẫn có thể dùng thử công cụ AI theo giới hạn quota hàng ngày.

### Các biến môi trường trong tệp `.env`:

Hãy chỉnh sửa file `.env` trong thư mục gốc của dự án để cấu hình Cloud AI:

```env
# 1. Các khóa API của nhà cung cấp trực tiếp (Server-side)
OPENAI_API_KEY=your_server_openai_api_key
GEMINI_API_KEY=your_server_gemini_api_key
CLAUDE_API_KEY=your_server_claude_api_key

# 2. Cấu hình Model sử dụng cho từng nhà cung cấp
OPENAI_MODEL=gpt-4.1-mini
GEMINI_MODEL=gemini-2.5-flash
CLAUDE_MODEL=claude-sonnet-4-20250514

# 3. Giới hạn lượt gọi thử nghiệm hàng ngày đối với Cloud AI
CLOUD_AI_PREVIEW_DAILY_LIMIT=30
```

---

## 4. Cấu Hình Cổng OpenAI-compatible Gateway / OpenClaw

Nếu tổ chức của bạn sử dụng một cổng gateway nội bộ hoặc bên thứ ba để quản lý và định tuyến lưu lượng AI (ví dụ: **OpenClaw** hoặc Cloudflare AI Gateway), bạn có thể cấu hình thông qua cổng tương thích OpenAI.

### Cấu hình biến môi trường tương thích:

Khi các biến này được thiết lập, mọi yêu cầu Cloud AI gửi tới nhà cung cấp `openai` sẽ được định tuyến lại qua cổng tùy chỉnh này:

```env
# URL cơ sở của Gateway tương thích (ví dụ: OpenClaw)
OPENAI_COMPATIBLE_BASE_URL=https://openclaw.yourcompany.com/v1

# API Key để xác thực với Gateway tương thích
OPENAI_COMPATIBLE_API_KEY=claw-secret-token-key

# Tên mô hình mà Gateway của bạn đang hỗ trợ và định tuyến
OPENAI_COMPATIBLE_MODEL=gateway-model-name
```

### Cách nhận diện nhãn tự động trên UI:
Hệ thống tự động phát hiện chuỗi trong `OPENAI_COMPATIBLE_BASE_URL`:
- Nếu chứa từ khóa `openclaw` (không phân biệt chữ hoa/thường): Nhãn badge hiển thị trên giao diện sẽ là **`Cloud AI · OpenClaw`**.
- Đối với các URL tương thích khác: Nhãn badge hiển thị sẽ là **`Cloud AI · OpenAI-compatible`**.

---

## 5. Danh Sách Các Tham Số Môi Trường AI Đầy Đủ

Dưới đây là bảng tổng hợp tất cả các thông số cấu hình liên quan đến AI được định nghĩa trong file `app/core/config.py`:

| Tên biến môi trường trong `.env` | Kiểu dữ liệu | Giá trị mặc định | Mô tả chức năng |
|---|---|---|---|
| `OPENAI_API_KEY` | string | `None` | API Key OpenAI dùng cho chế độ Cloud AI. |
| `GEMINI_API_KEY` | string | `None` | API Key Google Gemini dùng cho chế độ Cloud AI. |
| `CLAUDE_API_KEY` | string | `None` | API Key Anthropic Claude dùng cho chế độ Cloud AI. |
| `OPENAI_MODEL` | string | `gpt-4.1-mini` | Model OpenAI mặc định được gọi. |
| `GEMINI_MODEL` | string | `gemini-2.5-flash` | Model Google Gemini mặc định được gọi. |
| `CLAUDE_MODEL` | string | `claude-sonnet-4-20250514` | Model Claude mặc định được gọi. |
| `OPENAI_COMPATIBLE_BASE_URL` | string | `None` | URL của Gateway tương thích OpenAI (OpenClaw). |
| `OPENAI_COMPATIBLE_API_KEY` | string | `None` | API Key xác thực của Gateway tương thích. |
| `OPENAI_COMPATIBLE_MODEL` | string | `None` | Tên mô hình của Gateway tương thích. |
| `AI_PROVIDER_TIMEOUT_SECONDS` | float | `25.0` | Thời gian tối đa (giây) chờ phản hồi từ nhà cung cấp AI. |
| `AI_MAX_INPUT_CHARS` | integer | `60000` | Giới hạn độ dài ký tự tối đa của dữ liệu đầu vào. |
| `CLOUD_AI_PREVIEW_DAILY_LIMIT` | integer | `30` | Lượt sử dụng Cloud AI dùng thử tối đa/ngày/user. |
