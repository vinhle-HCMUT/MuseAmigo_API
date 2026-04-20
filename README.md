# 🏛️ MuseAmigo - Tài Liệu Hướng Dẫn Kỹ Thuật
> **Dự án:** Hệ thống quản lý và tương tác cổ vật bảo tàng thông qua AI.
> **Backend Stack:** FastAPI | MySQL (Aiven) | Render | Google Gemini

---

## 1. 🗄️ Kết Nối Database Cloud (DBeaver)
Để xem và quản lý dữ liệu trực tiếp trên Cloud, các thành viên sử dụng **DBeaver** và thiết lập kết nối theo bảng thông số sau:

| Thông số | Giá trị |
| :--- | :--- |
| **Loại Database** | `MySQL` |
| **Server Host** | `mysql-36b29279-congvinh7304-44dd.g.aivencloud.com` |
| **Port** | `17987` |
| **Username** | `avnadmin` |
| **Password** | `AVNS_49Sy8nbA8N7g1IFYLmq` |
| **Database** | `defaultdb` |

> [!CAUTION]
> **CẢNH BÁO BẢO MẬT:** Tuyệt đối **KHÔNG** chuyển trạng thái Repository này sang **Public** khi còn chứa thông tin kết nối trên. Hãy sử dụng file `.env` để bảo mật khi code.

---

## 2. 🚀 Kiểm Thử Backend (API Testing)
Mọi thay đổi trên logic Backend sẽ được tự động cập nhật tại:
🔗 **Swagger UI:** [https://museamigo-backend.onrender.com/docs/](https://museamigo-backend.onrender.com/docs/)

### Hướng dẫn Test nhanh:
1. Truy cập vào link **Swagger UI** bên trên.
2. Chọn một Endpoint (Ví dụ: `GET /artifacts`).
3. Bấm **Try it out** -> **Execute**.
4. **Mã 200:** Thành công, dữ liệu JSON sẽ hiển thị bên dưới.

---

## 3. 🛠️ Quy Trình Cập Nhật Code (Workflow)
Khi có sự thay đổi logic tại máy Local (VS Code), thực hiện quy trình đẩy code để Render tự động Deploy:

1. **Cập nhật danh sách thư viện (nếu có cài mới):**
   ```bash
   pip freeze > requirements.txt
2. Commit và Push code lên GitHub:
```
   git add .
   git commit -m "feat: mô tả tính năng mới hoặc fix lỗi"
   git push origin main
```
Sau khi Push, Render sẽ mất khoảng 2-3 phút để build lại bản mới nhất.

4. Tích Hợp Vào Frontend Unity (C#)
Sử dụng đoạn code mẫu dưới đây để kết nối Unity với hệ thống Backend.

A. Cấu hình Base URL

C#

// Sử dụng HTTPS cho môi trường Production (Cloud)

private string baseUrl = "[https://museamigo-backend.onrender.com](https://museamigo-backend.onrender.com)";

B. Script mẫu lấy danh sách Cổ vật
C#
```
using UnityEngine;
using UnityEngine.Networking;
using System.Collections;

public class ArtifactService : MonoBehaviour 
{
    public IEnumerator GetArtifacts() 
    {
        string url = baseUrl + "/artifacts";
        
        using (UnityWebRequest webRequest = UnityWebRequest.Get(url)) 
        {
            // Gửi yêu cầu và đợi phản hồi
            yield return webRequest.SendWebRequest();
            
            if (webRequest.result == UnityWebRequest.Result.Success) 
            {
                Debug.Log("Dữ liệu nhận về: " + webRequest.downloadHandler.text);
                // Thực hiện Parse JSON tại đây...
            } 
            else 
            {
                Debug.LogError("Lỗi kết nối API: " + webRequest.error);
            }
        }
    }
}
```
5. Lưu Ý Quan Trọng
6. 
⚠️ Cơ chế Cold Start: Vì dự án đang dùng gói Render Free, server sẽ tự "ngủ" nếu không có người truy cập. Lần gọi API đầu tiên trong ngày có thể mất 30-50 giây để khởi động. Vui lòng kiên nhẫn ở lần chạy app đầu tiên.

🔄 Đồng bộ dữ liệu: Mọi dữ liệu chỉnh sửa qua DBeaver (Aiven) sẽ được cập nhật ngay lập tức cho toàn bộ người dùng App Unity mà không cần build lại App.
