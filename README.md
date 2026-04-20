MuseAmigo - Tài Liệu Hướng Dẫn Kỹ Thuật (Backend & Integration)

Tài liệu này hướng dẫn cách vận hành, cập nhật hệ thống Backend và cách kết nối dữ liệu dành cho toàn bộ thành viên trong nhóm MuseAmigo.

1. Thông Tin Kết Nối Database Cloud (Dành cho DBeaver)
Để xem và quản lý dữ liệu trực tiếp trên Cloud (Aiven), các thành viên cài đặt DBeaver và cấu hình kết nối như sau:

Loại Database: MySQL

Host: mysql-36b29279-congvinh7304-44dd.g.aivencloud.com

Port: 17987

Username: avnadmin

Password: AVNS_49Sy8nbA8N7g1IFYLmq

Default Database: defaultdb

CẢNH BÁO BẢO MẬT: Tuyệt đối KHÔNG upload file chứa các thông tin này lên các kho lưu trữ công khai (như GitHub Public) để tránh bị người lạ truy cập và xóa dữ liệu.

2. Cách Test Backend (Dành cho Dev Frontend & Tester)
Mọi thay đổi trên Backend sẽ được cập nhật trực tiếp tại URL:
=>>https://museamigo-backend.onrender.com/docs/

A. Kiểm tra bằng Swagger UI (Trực quan nhất)
Truy cập: https://museamigo-backend.onrender.com/docs/

Cách test: Chọn một hàm (ví dụ GET /artifacts) -> Bấm Try it out -> Bấm Execute.

Kết quả: Nếu thấy mã 200 và danh sách dữ liệu JSON, nghĩa là server đang hoạt động tốt.

3. Quy Trình Cập Nhật Code 
Khi Ethan chỉnh sửa code trong VS Code và muốn cập nhật lên Render, thực hiện các bước sau:

Cập nhật thư viện (nếu có): pip freeze > requirements.txt

Đẩy code lên GitHub:

Bash
git add .
git commit -m "Mô tả nội dung vừa sửa"
git push origin main
Render Auto-deploy: Server Render sẽ tự động phát hiện code mới và khởi động lại trong khoảng 2-3 phút.

4. Cách Gắn API vào Frontend Unity (Dành cho Dev Frontend)
Trong Script quản lý Network trên Unity, hãy đổi cấu hình URL như sau:

A. Cấu hình Base URL
C#
// Luôn sử dụng HTTPS để đảm bảo bảo mật trên Cloud
private string baseUrl = "https://museamigo-backend.onrender.com";

B. Ví dụ gọi API lấy danh sách cổ vật

C#

IEnumerator GetArtifacts() {
    string url = baseUrl + "/artifacts";
    using (UnityWebRequest webRequest = UnityWebRequest.Get(url)) {
        yield return webRequest.SendWebRequest();
        if (webRequest.result == UnityWebRequest.Result.Success) {
            Debug.Log("Dữ liệu nhận về: " + webRequest.downloadHandler.text);
        } else {
            Debug.LogError("Lỗi kết nối API: " + webRequest.error);
        }
    }
}
5. Lưu ý quan trọng cho cả nhóm
Cơ chế "Ngủ" của Render: Vì chúng ta dùng gói Free, nếu server không có ai truy cập trong một thời gian, nó sẽ tạm nghỉ. Lần đầu mở app có thể mất 30 - 50 giây để server "tỉnh dậy". Các lần sau sẽ nhanh bình thường.

Đồng bộ dữ liệu: Mọi dữ liệu cổ vật mới thêm vào qua DBeaver sẽ xuất hiện ngay lập tức trên App Unity của tất cả mọi người.

