# Phase 1 — Product Discovery

## 1.1 Phân tích bài toán thực tế

### Bối cảnh

Trong quá trình phát triển phần mềm hiện đại, GitHub là nền tảng quản lý mã nguồn phổ biến nhất với hơn 100 triệu developer trên toàn cầu. Mỗi repository chứa lượng lớn dữ liệu hoạt động: commits, pull requests, issues — phản ánh toàn bộ quá trình phát triển của dự án.

Tuy nhiên, GitHub chỉ cung cấp các thống kê cơ bản (tab Insights) và không cho phép:
- Tổng hợp phân tích nhiều repository cùng lúc
- Xem xu hướng hoạt động theo thời gian chi tiết
- So sánh hiệu suất contributor
- Xuất báo cáo hoặc tùy chỉnh metrics

### Bài toán

Xây dựng một hệ thống web cho phép developer cá nhân:
1. Đăng nhập bằng tài khoản GitHub
2. Kết nối và đồng bộ dữ liệu repository
3. Xem dashboard phân tích hoạt động phát triển phần mềm
4. Theo dõi xu hướng commits, pull requests, issues theo thời gian

Hệ thống giải quyết nhu cầu: **"Tôi muốn hiểu rõ hơn hoạt động phát triển trong các repository của mình thông qua dữ liệu trực quan."**

---

## 1.2 Pain Points của Developer

| # | Pain Point | Mô tả |
|---|---|---|
| 1 | GitHub Insights hạn chế | Chỉ hiển thị cho 1 repo, không tổng hợp được nhiều repos |
| 2 | Không có timeline dài hạn | GitHub chỉ hiển thị thống kê gần đây, khó xem trend 6-12 tháng |
| 3 | Không có PR metrics | Không biết average merge time, bottleneck ở đâu |
| 4 | Khó đánh giá bản thân | Developer muốn biết mình commit bao nhiêu, contribute ở đâu nhiều nhất |
| 5 | Không có issue overview | Bao nhiêu issue open, close rate bao nhiêu, label nào nhiều nhất |
| 6 | Phụ thuộc internet | Mỗi lần muốn xem phải vào GitHub, không có dashboard tập trung |

---

## 1.3 User Personas

### Persona 1: Sinh viên CNTT — "Minh"

| Thuộc tính | Mô tả |
|---|---|
| Tuổi | 21 |
| Vai trò | Sinh viên năm 4, đang làm đồ án tốt nghiệp |
| Nhu cầu | Muốn theo dõi tiến độ code đồ án, xem mình commit đều hay không |
| Hành vi | Có 3-5 private repos, commit không đều, thỉnh thoảng quên push |
| Mục tiêu | Dùng dashboard để tự đánh giá và đưa vào portfolio |

### Persona 2: Junior Developer — "Hùng"

| Thuộc tính | Mô tả |
|---|---|
| Tuổi | 24 |
| Vai trò | Junior developer tại startup, contribute vào 2-3 repos |
| Nhu cầu | Muốn biết PR merge time trung bình, mình review bao nhiêu |
| Hành vi | Commit hàng ngày, tạo PR thường xuyên, track issues |
| Mục tiêu | Cải thiện workflow, report cho team lead |

### Persona 3: Freelancer — "Lan"

| Thuộc tính | Mô tả |
|---|---|
| Tuổi | 28 |
| Vai trò | Freelance developer, làm nhiều projects song song |
| Nhu cầu | Muốn tổng hợp activity across repos để báo cáo cho khách hàng |
| Hành vi | Nhiều repos nhỏ, commit không đều, cần proof of work |
| Mục tiêu | Dashboard đẹp để show cho clients |

**MVP tập trung phục vụ Persona 1 và 2** — Individual developer muốn phân tích repos của chính mình.

---

## 1.4 Use Cases chính

### UC-01: Đăng nhập bằng GitHub
- **Actor**: User (chưa đăng nhập)
- **Mô tả**: User nhấn nút "Login with GitHub", được redirect sang GitHub OAuth, cấp quyền, redirect về hệ thống với session đã authenticated.
- **Postcondition**: User có session hợp lệ, hệ thống lưu access token encrypted.

### UC-02: Xem danh sách repositories
- **Actor**: User (đã đăng nhập)
- **Mô tả**: User xem danh sách các repos mà mình có quyền truy cập trên GitHub (public + private).
- **Postcondition**: Hiển thị danh sách repos với tên, mô tả, ngôn ngữ chính, visibility.

### UC-03: Kết nối repository để phân tích
- **Actor**: User
- **Mô tả**: User chọn một hoặc nhiều repos từ danh sách để thêm vào hệ thống phân tích.
- **Postcondition**: Repository được lưu vào database với trạng thái chưa sync.

### UC-04: Đồng bộ dữ liệu repository
- **Actor**: User
- **Mô tả**: User nhấn nút "Sync" trên một repository đã kết nối. Hệ thống gọi GitHub API để lấy commits, PRs, issues và lưu vào database.
- **Precondition**: Repository đã được kết nối, GitHub API quota đủ.
- **Postcondition**: Dữ liệu mới nhất được lưu, `last_synced_at` cập nhật.
- **Exception**: Nếu rate limit exceeded → dừng sync, lưu lỗi.

### UC-05: Xem Dashboard Overview
- **Actor**: User
- **Mô tả**: User mở trang Overview, thấy summary cards (total commits, PRs, issues, last sync) và biểu đồ tổng quan.
- **Precondition**: Repository đã sync ít nhất 1 lần.

### UC-06: Xem Commit Analytics
- **Actor**: User
- **Mô tả**: User mở trang Commits, xem biểu đồ commits/day, commits by contributor, recent commits list.

### UC-07: Xem Pull Request Analytics
- **Actor**: User
- **Mô tả**: User mở trang Pull Requests, xem PR status distribution, average merge time, PR by author.

### UC-08: Xem Issue Analytics
- **Actor**: User
- **Mô tả**: User mở trang Issues, xem open/closed chart, issues by label, average time to close.

### UC-09: Đăng xuất
- **Actor**: User
- **Mô tả**: User nhấn Logout. Session bị xóa, cookie bị clear.

### UC-10: Xem Developer Insights
- **Actor**: User
- **Mô tả**: User mở trang Insights của repository đã sync để xem phân tích hành vi nâng cao: heatmap đóng góp 365 ngày, streak hiện tại/dài nhất, activity score, phân bố keyword conventional commits, commits by hour/weekday, PR throughput, issue closure rate.

### UC-11: Xem Ecosystem Explore Feed
- **Actor**: User
- **Mô tả**: User mở trang Explore để xem bảng tin hệ sinh thái lập trình: các repository GitHub đang trending (có bộ lọc ngôn ngữ), tin tức công nghệ hàng đầu từ Hacker News, và danh mục công cụ phát triển/AI LLM nổi bật được cập nhật qua cơ chế in-memory TTL caching.

---

## 1.5 Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Đăng nhập/đăng xuất bằng GitHub OAuth | Must have |
| FR-02 | Hiển thị danh sách repositories từ GitHub | Must have |
| FR-03 | Kết nối repository vào hệ thống | Must have |
| FR-04 | Đồng bộ commits từ GitHub API | Must have |
| FR-05 | Đồng bộ pull requests từ GitHub API | Must have |
| FR-06 | Đồng bộ issues từ GitHub API | Must have |
| FR-07 | Incremental sync (chỉ lấy data mới) | Must have |
| FR-08 | Hiển thị Dashboard Overview | Must have |
| FR-09 | Hiển thị Commit Analytics | Must have |
| FR-10 | Hiển thị Pull Request Analytics | Must have |
| FR-11 | Hiển thị Issue Analytics | Must have |
| FR-12 | Kiểm tra rate limit trước khi sync | Should have |
| FR-13 | Hiển thị trạng thái sync (thành công/lỗi) | Should have |
| FR-14 | Hiển thị thông tin rate limit remaining | Could have |
| FR-15 | Ngắt kết nối repository (xóa dữ liệu đã sync) | Could have |

---

## 1.6 Non-Functional Requirements

| ID | Requirement | Mô tả |
|---|---|---|
| NFR-01 | Security | GitHub token phải encrypted, không log, không expose ra client |
| NFR-02 | Performance | Dashboard load < 3 giây cho repo ≤ 5,000 commits |
| NFR-03 | Reliability | Sync failure không làm mất data đã sync trước đó |
| NFR-04 | Usability | UI trực quan, developer không cần đọc hướng dẫn để sử dụng |
| NFR-05 | Maintainability | Clean Architecture, code dễ đọc, dễ test |
| NFR-06 | Portability | Chạy được trên SQLite (dev) và PostgreSQL (production) |
| NFR-07 | Scalability | Thiết kế cho phép mở rộng thêm Team/Org features sau này |
| NFR-08 | Availability | Deploy trên Railway/Render, uptime phụ thuộc platform |

---

## 1.7 Phạm vi MVP

### Trong scope MVP

| Module | Features |
|---|---|
| Authentication | GitHub OAuth login/logout, encrypted token storage |
| Repository Management | List repos, connect/disconnect repo |
| Data Sync | Incremental sync commits/PRs/issues, rate limit check, error handling |
| Dashboard - Overview | Summary cards, activity timeline |
| Dashboard - Commits | Commits/day, commits by contributor, recent commits |
| Dashboard - Pull Requests | PR status, merge time, PR by author |
| Dashboard - Issues | Open/closed, by label, time to close |
| Dashboard - Insights | Heatmap đóng góp 365 ngày, streak coding, activity score, commits by hour/weekday, PR throughput, issue closure rate |
| Ecosystem - Explore | Bảng tin GitHub trending (bộ lọc ngôn ngữ), Hacker News top stories, AI/LLM developer tools, in-memory TTL caching |
| Modern Dark Theme | Giao diện Vercel/Linear dark theme cao cấp, responsive sử dụng Vanilla CSS |
| API | RESTful JSON endpoints cho analytics, insights, và explore/trending |

### Ngoài scope MVP (Out-of-scope)

| Feature | Lý do loại |
|---|---|
| Team/Organization management | Scope quá lớn, thuộc hướng B |
| Reviewer analysis | Cần thêm API calls per PR |
| Code additions/deletions stats | Cần 1 request/commit, tốn quota |
| Background auto-sync | Cần task queue (Celery/APScheduler), phức tạp |
| Real-time updates (WebSocket) | Không cần thiết cho analytics dashboard |
| Email notifications | Không liên quan đến core value |
| Export PDF/CSV reports | Nice-to-have, defer |
| GitHub App (fine-grained permissions) | Phức tạp hơn OAuth, defer cho production |
| Multi-provider (GitLab, Bitbucket) | Scope quá lớn |
| Custom date range filter | Nice-to-have, có thể thêm cuối MVP |

---

## 1.8 Competitive Analysis

| Tiêu chí | GitHub Insights | GitLab Analytics | Jira Dashboard | **Git Analytics (Hệ thống này)** |
|---|---|---|---|---|
| Phân tích commits | ✅ Cơ bản (1 repo) | ✅ Tốt | ❌ | ✅ Nhiều repos |
| PR metrics | ❌ | ✅ Merge time | ❌ | ✅ Merge time, status |
| Issue tracking | ❌ | ✅ | ✅ Rất tốt | ✅ Cơ bản |
| Multi-repo | ❌ | ❌ | ❌ | ✅ |
| Custom dashboard | ❌ | ❌ | ✅ | ⚠️ Fixed 5 pages + Explore |
| Free for individuals | ✅ | ✅ (limited) | ❌ (paid) | ✅ |
| Self-hosted | ❌ | ✅ | ❌ | ✅ |
| API-first | ❌ | ✅ | ✅ | ✅ |
| Offline data | ❌ | ❌ | N/A | ✅ (synced to DB) |

### Điểm khác biệt của hệ thống

1. **Tập trung vào cá nhân** — không phải enterprise tool
2. **Multi-repo analytics** — tổng hợp từ nhiều repos cá nhân
3. **Offline-capable** — data sync vào DB, xem dashboard không cần GitHub online
4. **Open-source, self-hosted** — developer có thể tự deploy
5. **API-first** — data có thể tái sử dụng cho tools khác

---

## 1.9 Feature Priority Roadmap

### MVP (4-6 tuần)

| Priority | Feature |
|---|---|
| P0 | GitHub OAuth login/logout |
| P0 | List & connect repositories |
| P0 | Sync commits (incremental) |
| P0 | Sync pull requests |
| P0 | Sync issues |
| P0 | Dashboard Overview page |
| P0 | Dashboard Commits page |
| P1 | Dashboard Pull Requests page |
| P1 | Dashboard Issues page |
| P1 | Rate limit pre-check |
| P1 | Sync error handling & status display |

### Post-MVP (Enhancement)

| Priority | Feature |
|---|---|
| P2 | Date range filter cho charts |
| P2 | Disconnect/remove repository |
| P2 | Multiple repo comparison |
| P2 | Commit detail stats (additions/deletions) — hybrid mode |
| P3 | PR reviewer analysis |
| P3 | Contributor alias merging |
| P3 | Export CSV |
| P3 | Background auto-sync |

### Future (v2.0+)

| Priority | Feature |
|---|---|
| P4 | Team/Organization dashboard |
| P4 | GitHub App migration (fine-grained permissions) |
| P4 | GitLab integration |
| P4 | Custom metrics & alerts |
| P4 | AI-powered insights (commit patterns, burnout detection) |

---

## 1.10 Rủi ro và giải pháp

| Rủi ro | Xác suất | Tác động | Giải pháp |
|---|---|---|---|
| GitHub rate limit exceeded khi demo | Trung bình | Cao | Pre-check quota, dùng repo nhỏ khi demo |
| OAuth token bị revoke | Thấp | Trung bình | Xử lý 401, yêu cầu re-login |
| Repo quá lớn (>10,000 commits) | Trung bình | Trung bình | Giới hạn sync hoặc pagination cẩn thận |
| GitHub API thay đổi | Thấp | Cao | Dùng adapter pattern, dễ cập nhật |
| Demo bị lỗi mạng | Trung bình | Cao | Data đã sync vẫn xem được dashboard offline |

---

*Kết thúc Phase 1 — Product Discovery. Tiếp theo: Phase 2 — System Design.*
