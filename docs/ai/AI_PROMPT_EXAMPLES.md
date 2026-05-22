# Các Ví Dụ Thực Tế & Kỹ Năng Prompting — Git Analytics

Tài liệu này cung cấp các kịch bản sử dụng thực tế, ví dụ về đầu vào hợp lệ/không hợp lệ, các câu hỏi khuyến nghị cho trợ lý ảo, và các kỹ năng viết prompt để tối ưu hóa kết quả đầu ra từ hệ thống AI trên ứng dụng **Git Analytics**.

---

## 1. Ví Dụ Về Mã Đầu Vào (Git Diff Input)

Hệ thống tích hợp bộ lọc xác thực để ngăn chặn việc gửi mã nguồn rác hoặc đầu vào không phải là Git Diff tới các nhà cung cấp AI nhằm tối ưu hóa chi phí token.

### ✅ Ví dụ Git Diff hợp lệ (Valid Diff Input)
Đây là cấu trúc một đoạn Git Diff tiêu chuẩn được tạo ra từ lệnh `git diff`. Bạn có thể dán trực tiếp định dạng này vào khung nhập liệu của **Commit Message** hoặc **PR Review**:

```diff
diff --git a/app/services/ai_provider_service.py b/app/services/ai_provider_service.py
index a1b2c3d..e5f6g7h 100644
--- a/app/services/ai_provider_service.py
+++ b/app/services/ai_provider_service.py
@@ -216,3 +216,15 @@ class AiToolService:
     async def generate_commit_message(self, *, user_id: int, diff: str) -> dict[str, Any]:
         clean_diff = self._validate_input(diff, "diff")
+        self._validate_git_diff(clean_diff)
         completion = await self._complete(
             user_id=user_id,
             operation="commit_message",
             system_prompt=(
                 "Generate one concise Conventional Commit message for the provided git diff. "
                 "Return only the commit message."
             ),
             user_prompt=clean_diff,
         )
         message = completion.text.splitlines()[0].strip().strip("`")
-        return {"message": message[:240], "files": _changed_files(clean_diff)[:12]}
+        metadata = self.settings_service.get_active_provider_metadata(user_id)
+        return {
+            "message": message[:240],
+            "files": _changed_files(clean_diff)[:12],
+            "metadata": metadata,
+        }
```

### ❌ Ví dụ mã đầu vào KHÔNG hợp lệ (Invalid Input)
Dán các dòng mã tự do, mô tả bằng chữ thường hoặc log commit không có header định dạng diff sẽ bị hệ thống chặn lại lập tức với lỗi `Invalid git diff format provided.`

```text
Tôi vừa sửa file service.py bằng cách thêm hàm validate và cập nhật phương thức trả về metadata. Hãy viết hộ tôi một commit message.
```
*Lưu ý: Hãy luôn sử dụng lệnh `git diff` trong terminal để tạo ra văn bản thay đổi chính xác trước khi dán vào giao diện web.*

---

## 2. Các Kịch Bản & Câu Hỏi Khuyến Nghị Cho Trợ Lý Ảo (Repo Assistant)

Khi sử dụng **Repo Assistant**, bạn có thể hỏi bất kỳ câu hỏi nào về thiết kế hệ thống, nghiệp vụ hoặc tìm lỗi trong repository. Dưới đây là các nhóm câu hỏi khuyến nghị mẫu đã được kiểm chứng cho hiệu quả phản hồi tối ưu:

### 🔐 Chủ đề: Bảo mật & Xác thực (Authentication Flow)
> **Câu hỏi khuyến nghị:**
> *"Auth flow của app này hoạt động như thế nào? Từ lúc người dùng click đăng nhập bằng GitHub ở frontend cho đến khi lưu Session cookie ở backend đi qua những file nào và được xử lý ra sao?"*

### 🔄 Chủ đề: Cơ chế Đồng bộ dữ liệu (Data Sync Architecture)
> **Câu hỏi khuyến nghị:**
> *"Kiến trúc đồng bộ repository (Sync Service) đi qua những service, repository và model nào? Luồng xử lý khi người dùng ấn nút Sync hoạt động tuần tự như thế nào?"*

### ⚠️ Chủ đề: Đánh giá Rủi ro trước khi thay đổi (Impact Analysis)
> **Câu hỏi khuyến nghị:**
> *"Những file nào có rủi ro cao hoặc có mức độ ảnh hưởng lớn nhất trong hệ thống mà tôi cần lưu ý trước khi tiến hành sửa đổi logic tính toán của module Analytics?"*

### 🧪 Chủ đề: Thiết kế Kiểm thử (Test Case Design)
> **Câu hỏi khuyến nghị:**
> *"Đề xuất bộ kịch bản kiểm thử (test cases) đầy đủ cho chức năng chuyển đổi qua lại giữa cấu hình BYOK (Gemini, OpenAI, Claude) và Cloud AI (cổng OpenClaw/OpenAI-compatible) ở backend."*

---

## 3. Bí Quyết Viết Prompt Để Nhận Được Phản Hồi Tốt Nhất

Hệ thống AI hoạt động hiệu quả nhất khi bạn cung cấp đầy đủ thông tin ngữ cảnh. Hãy áp dụng 4 nguyên tắc sau để nhận được câu trả lời chất lượng cao:

1. **Cụ thể hóa câu hỏi (Be Specific):**
   - *Thay vì hỏi:* "Chỉ tôi cách viết test cho api."
   - *Hãy hỏi:* "Đề xuất cấu trúc file test và viết mẫu một pytest kiểm thử tích hợp cho API endpoint `/api/v1/ai/commit-message` với dữ liệu giả lập (mocking) API Gateway."

2. **Dán mã nguồn có liên quan (Paste Relevant Context):**
   - Khi hỏi về lỗi hoặc cấu trúc của một hàm/file cụ thể, hãy dán trực tiếp một phần mã nguồn của file đó hoặc chỉ rõ đường dẫn file (ví dụ: `app/services/ai_provider_service.py`) để mô hình LLM khoanh vùng phạm vi chính xác.

3. **Hỏi một tác vụ tại một thời điểm (Ask One Task at a Time):**
   - Đừng gộp quá nhiều yêu cầu vào một câu hỏi lớn (ví dụ: vừa yêu cầu giải thích luồng, vừa bắt viết test, vừa bắt tìm lỗi bảo mật). Hãy chia nhỏ và hỏi trợ lý theo từng bước độc lập.

4. **Chỉ định rõ Module mục tiêu (Mention Target Module):**
   - Nhắc đến các công nghệ và thư viện đang được sử dụng trong hệ thống như `FastAPI`, `SQLAlchemy 2.0`, `Jinja2` hay `pytest` để trợ lý ảo trả về các ví dụ khớp hoàn toàn với kiến trúc kỹ thuật hiện tại của dự án.
