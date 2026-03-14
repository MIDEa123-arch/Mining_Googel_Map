# Mining_Googel_Map

Vào trong code đổi CAU_HINH_CHUYEN_MUC được phân công để mine. Code chạy lâu lên đến hơn 1 ngày lận nên cần phải treo, code lỗi hoặc bị ngắt thì cứ bấm chạy lại (nên chạy thử 1-5 quán để xem code chạy đúng ko ko đúng kêu t)

Nếu xem file mà thấy tọa độ bị trùng thì chạy file fixLocation để fix nha và nếu thấy output có lỗi như 00x00... dì đó thì sửa cái tên chuyên mục lại 
vd: "Quán karaoke" -> "karaoke" do Quán karaoke + Tên quận nó nhảy thẳng vô địa điểm luôn nên bị lỗi 

```python
HUY:
CAU_HINH_CHUYEN_MUC = {
    # Phổ thông
    "Rạp chiếu phim": 3, 
    "Quán karaoke": 8, 
    "Trung tâm giải trí": 5, 
    "Khu vui chơi": 5,

    # Thể thao/Vận động
    "Phòng bida": 8, 
    "Sân bóng đá mini": 5, 
    "Sân tennis": 3, 
    "Hồ bơi": 4, 
    "Sân trượt băng": 1,  # Hiếm, để 1-2 cái thôi

    # Nghệ thuật
    "Sân khấu kịch": 2, 
    "Phòng hòa nhạc": 1
}

PHƯỚC:
CAU_HINH_CHUYEN_MUC = {
    # Văn hóa/Lịch sử
    "Bảo tàng": 2, 
    "Di tích lịch sử": 3, 
    "Dinh thự lịch sử": 1, 
    "Địa điểm tham quan văn hóa": 4,

    # Tâm linh
    "Chùa": 8, 
    "Đền": 3, 
    "Nhà thờ": 5, 
    "Tu viện": 2,

    # Thiên nhiên/Cảnh quan
    "Công viên": 5, 
    "Vườn bách thảo": 1, 
    "Sở thú": 1, 
    "Điểm ngắm cảnh": 3, 
    "Khu du lịch sinh thái": 2,

    # Đặc trưng địa phương
    "Điểm tham quan du lịch": 5, 
    "Chợ nổi": 1
}

LÂM:
CAU_HINH_CHUYEN_MUC = {
    # Nhóm Shopping
    "Trung tâm thương mại": 3,  # Mall thì 1 quận có 2-3 cái là căng
    "Siêu thị": 8, 
    "Chợ": 5, 
    "Chợ đêm": 2, 
    "Cửa hàng đặc sản": 5,
    "Phố mua sắm": 3
}
```
