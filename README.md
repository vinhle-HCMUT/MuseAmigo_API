# 🏛️ MuseAmigo - Backend API Service

⚡ **Hệ thống quản lý và tương tác cổ vật bảo tàng thông qua trí tuệ nhân tạo (AI).**

<p align="left">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=FastAPI&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL" />
  <img src="https://img.shields.io/badge/Google%20Gemini-8E75C2?style=for-the-badge&logo=googlegemini&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Render-000000?style=for-the-badge&logo=render&logoColor=white" alt="Render" />
</p>

---

## 📖 Tổng Quan Dự Án
MuseAmigo là giải pháp công nghệ số hóa trải nghiệm bảo tàng. Hệ thống Backend cung cấp các RESTful API phục vụ việc quản lý thông tin cổ vật, đồng thời tích hợp mô hình ngôn ngữ lớn (LLM) **Google Gemini** để tự động tạo nội dung tương tác, giải đáp và cung cấp thông tin chuyên sâu về hiện vật cho người dùng cuối trên ứng dụng client.

## ✨ Các Tính Năng Cốt Lõi
* **Quản lý Cổ vật (CRUD):** API tối ưu hiệu năng để truy xuất, cập nhật danh mục hiện vật.
* **Tích hợp AI (Google Gemini):** Phân tích ngữ cảnh, tự động sinh nội dung tương tác và thuyết minh cổ vật tự động.
* **Đồng bộ thời gian thực:** Kết nối cơ sở dữ liệu Cloud giúp dữ liệu cập nhật tức thì lên client mà không cần build lại ứng dụng.

---

## 1. 🗄️ Cấu Hình Cơ Sở Dữ Liệu Cloud

Hệ thống sử dụng cơ sở dữ liệu **MySQL** được host trên nền tảng **Aiven Cloud**. Để quản lý và xem dữ liệu trực tiếp, các thành viên sử dụng công cụ **DBeaver** và cấu hình theo các thông số dưới đây:

| Thông số | Giá trị định cấu hình |
| :--- | :--- |
| **Loại Database** | `MySQL` |
| **Server Host** | `mysql-36b29279-congvinh7304-44dd.g.aivencloud.com` |
| **Port** | `17987` |
| **Username** | `avnadmin` |
| **Database** | `defaultdb` |
| **Password** | *Vui lòng lấy trong file `.env` cục bộ hoặc kênh trao đổi nội bộ* |

> [!IMPORTANT]
> **Hướng dẫn Bảo mật:** Để bảo vệ an toàn cho hệ thống, toàn bộ thông tin nhạy cảm bao gồm mật khẩu kết nối database và API Key của Google Gemini đã được đưa vào biến môi trường. Vui lòng tạo một file `.env` ở thư mục gốc của dự án dựa trên mẫu dưới đây:

```env
# Mẫu cấu hình tệp .env cục bộ
DB_HOST=mysql-36b29279-congvinh7304-44dd.g.aivencloud.com
DB_PORT=17987
DB_USER=avnadmin
DB_PASSWORD=YOUR_SECRET_PASSWORD_HERE
DB_NAME=defaultdb
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE

## 2. 🚀 Kiểm Thử & Trải Nghiệm API (API Testing)

Mọi thay đổi trên logic Backend khi được đẩy lên nhánh chính sẽ tự động kích hoạt quy trình CI/CD và deploy lên môi trường Cloud. Bạn có thể kiểm thử trực tiếp các endpoint tại:

🔗 **Swagger UI Documentation:** [https://museamigo-backend.onrender.com/docs/](https://museamigo-backend.onrender.com/docs/)

### Các bước kiểm thử nhanh:
1. Truy cập liên kết **Swagger UI** ở trên.
2. Lựa chọn Endpoint bạn muốn kiểm tra (Ví dụ: `GET /artifacts` để lấy danh sách cổ vật).
3. Nhấp chọn **Try it out** -> Chọn **Execute**.
4. Phản hồi thành công sẽ trả về mã lỗi **200 OK** kèm theo cấu trúc dữ liệu định dạng JSON trực quan ở phía dưới.
## 3. 🛠️ Quy Trình Cập Nhật Code (Git Workflow)

Khi thực hiện cải tiến logic hoặc sửa lỗi tại máy local (VS Code), vui lòng tuân thủ quy trình đồng bộ hóa mã nguồn để hệ thống Render tự động cập nhật phiên bản mới:

1. **Cập nhật danh sách thư viện phụ thuộc (nếu có cài đặt package mới):**
   ```bash
   pip freeze > requirements.txt
2. **Đóng gói mã nguồn và đẩy lên GitHub:**
   ```bash
   git add .
   git commit -m "feat: mô tả chi tiết tính năng mới hoặc bản sửa lỗi"
   git push origin main
## 4. ⚠️ Các Lưu Ý Kỹ Thuật Quan Trọng

* **Cơ chế Cold Start (Khởi động lạnh):** Do dịch vụ Backend hiện tại đang được triển khai trên gói tài nguyên miễn phí của Render, máy chủ sẽ tự động chuyển sang trạng thái "ngủ" (Sleep) nếu không phát sinh lượt truy cập nào trong thời gian dài. Lần gọi API đầu tiên trong ngày có thể mất từ **30 - 50 giây** để khởi động lại cụm container. Vui lòng kiên nhẫn trong lần tải ứng dụng đầu tiên.
* **Cập nhật dữ liệu tức thì:** Mọi thao tác thay đổi cấu trúc hoặc bản ghi dữ liệu thông qua công cụ quản trị DBeaver sẽ có hiệu lực ngay lập tức. Hệ thống Client sẽ nhận được dữ liệu mới hoàn toàn mà không cần phải tiến hành đóng gói (Re-build) lại.
