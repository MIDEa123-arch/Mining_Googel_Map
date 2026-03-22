import pandas as pd
import time
import re
import sys
import os

from selenium import webdriver
# ĐỔI THÀNH FIREFOX OPTIONS:
from selenium.webdriver.firefox.options import Options 
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Quản lý driver tự động
from webdriver_manager.firefox import GeckoDriverManager

sys.stdout.reconfigure(encoding='utf-8')

# ==========================================
# CẤU HÌNH
# ==========================================
FILE_INPUT = "../Data_ToanTap_AmThuc_HCM.csv"
FILE_BACKUP = "Data_ToanTap_AmThuc_HCM_BACKUP.csv"
FILE_CHECKPOINT = "fix_smart_checkpoint.csv"

print("="*70)
print("🧠 CÔNG CỤ SỬA TỌA ĐỘ THÔNG MINH")
print("   • Giữ nguyên quán đầu tiên mỗi nhóm trùng")
print("   • Chỉ sửa quán bị trùng (quán thứ 2, 3, 4...)")
print("   • Tự động retry nếu sau khi sửa vẫn còn trùng >2 lần")
print("="*70)

# ==========================================
# 1. BACKUP FILE GỐC
# ==========================================
print(f"\n📦 Bước 1: Backup file gốc...")
try:
    df_original = pd.read_csv(FILE_INPUT, encoding='utf-8-sig')
    df_original.to_csv(FILE_BACKUP, index=False, encoding='utf-8-sig')
    print(f"   ✅ Đã backup sang: {FILE_BACKUP}")
except Exception as e:
    print(f"   ❌ Lỗi khi backup: {e}")
    exit(1)

# ==========================================
# 2. PHÂN TÍCH TỌA ĐỘ TRÙNG
# ==========================================
def phan_tich_toa_do_trung(df):
    """Phân tích và trả về danh sách các nhóm tọa độ trùng"""
    df_temp = df.copy()
    df_temp['ToaDo'] = df_temp['ToaDo'].fillna('')
    
    # Đếm số lần xuất hiện của mỗi tọa độ
    toa_do_counts = df_temp[df_temp['ToaDo'] != '']['ToaDo'].value_counts()
    toa_do_trung = toa_do_counts[toa_do_counts > 1]
    
    # Tạo dict: tọa độ -> danh sách index
    nhom_trung = {}
    for toa_do, count in toa_do_trung.items():
        indices = df_temp[df_temp['ToaDo'] == toa_do].index.tolist()
        nhom_trung[toa_do] = indices
    
    return nhom_trung, toa_do_counts

print(f"\n🔍 Bước 2: Phân tích tọa độ trùng...")
df = df_original.copy()
nhom_trung, toa_do_counts = phan_tich_toa_do_trung(df)

print(f"   📊 Tổng số quán: {len(df)}")
print(f"   🔴 Số tọa độ bị trùng: {len(nhom_trung)}")

if len(nhom_trung) == 0:
    print(f"\n   ✅ Không có tọa độ trùng! File đã OK.")
    exit(0)

# Hiển thị top tọa độ trùng nhiều nhất
print(f"\n   Top 10 tọa độ trùng nhiều nhất:")
sorted_nhom = sorted(nhom_trung.items(), key=lambda x: len(x[1]), reverse=True)
for i, (toa_do, indices) in enumerate(sorted_nhom[:10], 1):
    print(f"      {i}. {toa_do} - {len(indices)} quán")
    print(f"         → Giữ nguyên: {df.loc[indices[0], 'TenDiaDiem'][:40]}")
    print(f"         → Sửa {len(indices)-1} quán còn lại")

# ==========================================
# 3. TẠO DANH SÁCH CẦN SỬA
# ==========================================
print(f"\n📝 Bước 3: Tạo danh sách quán cần sửa...")

danh_sach_can_sua = []
danh_sach_giu_nguyen = []

for toa_do, indices in nhom_trung.items():
    # GIỮ NGUYÊN quán đầu tiên
    danh_sach_giu_nguyen.append(indices[0])
    
    # CHỈ SỬA các quán còn lại
    danh_sach_can_sua.extend(indices[1:])

print(f"   • Tổng quán bị trùng: {sum(len(v) for v in nhom_trung.values())}")
print(f"   • Quán giữ nguyên (đầu tiên mỗi nhóm): {len(danh_sach_giu_nguyen)}")
print(f"   • Quán cần sửa: {len(danh_sach_can_sua)}")

# ==========================================
# LOAD CHECKPOINT (NẾU CÓ)
# ==========================================
da_xu_ly = set()
if os.path.exists(FILE_CHECKPOINT):
    print(f"\n🔄 Phát hiện checkpoint!")
    try:
        df_checkpoint = pd.read_csv(FILE_CHECKPOINT)
        da_xu_ly = set(df_checkpoint['Index'].tolist())
        print(f"   📊 Đã xử lý trước đó: {len(da_xu_ly)} quán")
        
        choice = input("\n   [1] RESUME [2] Bắt đầu lại: ").strip()
        if choice != '1':
            os.remove(FILE_CHECKPOINT)
            da_xu_ly = set()
            print(f"   🗑️ Đã xóa checkpoint")
    except:
        da_xu_ly = set()

# ==========================================
# 4. KHỞI TẠO SELENIUM
# ==========================================
print(f"\n🚀 Bước 4: Khởi động trình duyệt...")
chrome_options = Options()
# chrome_options.add_argument("--headless=new")  # Bỏ comment để chạy ẩn
firefox_options = Options()
# firefox_options.add_argument("--headless")  # Bật dòng này nếu muốn chạy ẩn (không hiện cửa sổ)

# 2. Khởi tạo Driver (Dùng webdriver-manager để tự động quản lý driver)
driver = webdriver.Firefox(
    service=Service(GeckoDriverManager().install()), 
    options=firefox_options
)

driver.get("https://www.google.com/maps?hl=vi")
time.sleep(2)

# ==========================================
# HÀM LẤY TỌA ĐỘ
# ==========================================
def lay_toa_do_chinh_xac(ten_quan, dia_chi, quan):
    """Tìm kiếm quán trên Google Maps và lấy tọa độ chính xác"""
    try:
        url_cu = driver.current_url
        
        # Tạo query tìm kiếm
        if dia_chi and dia_chi.strip():
            query = f"{ten_quan}, {dia_chi}"
        else:
            query = f"{ten_quan}, {quan}, Hồ Chí Minh"
        
        # Tìm kiếm
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.ENTER)
        
        time.sleep(2)
        
        # Click vào kết quả đầu tiên
        try:
            first_result = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.hfpxzc"))
            )
            driver.execute_script("arguments[0].click();", first_result)
        except:
            pass
        
        # Đợi URL thay đổi
        thoi_gian_cho = 0
        while driver.current_url == url_cu and thoi_gian_cho < 10:
            time.sleep(0.5)
            thoi_gian_cho += 0.5
        
        time.sleep(1)
        
        # Lấy tọa độ từ URL
        url_moi = driver.current_url
        match = re.search(r'@([-+]?\d+\.\d+),([-+]?\d+\.\d+)', url_moi)
        if match:
            toa_do_moi = f"{match.group(1)}, {match.group(2)}"
            return toa_do_moi, True
        
        return "", False
        
    except Exception as e:
        return "", False

# ==========================================
# 5. VÒNG SỬA - CÓ THỂ CHẠY NHIỀU LẦN
# ==========================================
vong_sua = 1
MAX_VONG = 3  # Tối đa chạy 3 vòng

while vong_sua <= MAX_VONG:
    print(f"\n" + "="*70)
    print(f"🔄 VÒNG {vong_sua}: SỬA TỌA ĐỘ")
    print("="*70)
    
    # Lọc danh sách cần sửa (bỏ qua đã xử lý)
    danh_sach_vong_nay = [idx for idx in danh_sach_can_sua if idx not in da_xu_ly]
    
    if len(danh_sach_vong_nay) == 0:
        print(f"   ✅ Không còn quán nào cần sửa trong vòng này!")
        break
    
    print(f"   📝 Số quán cần sửa vòng này: {len(danh_sach_vong_nay)}")
    print(f"   ⏱️ Ước tính: ~{len(danh_sach_vong_nay) * 6 / 60:.1f} phút\n")
    
    so_thanh_cong = 0
    so_that_bai = 0
    so_khong_doi = 0
    
    # Tạo checkpoint file nếu chưa có
    if not os.path.exists(FILE_CHECKPOINT):
        pd.DataFrame(columns=['Index', 'TenDiaDiem', 'ToaDoMoi', 'TrangThai']).to_csv(
            FILE_CHECKPOINT, index=False, encoding='utf-8-sig'
        )
    
    try:
        for idx_count, i in enumerate(danh_sach_vong_nay, 1):
            row = df.loc[i]
            ten = row['TenDiaDiem']
            dia_chi = row['DiaChi'] if pd.notna(row['DiaChi']) else ''
            quan = row['Quan']
            toa_do_cu = row['ToaDo']
            
            print(f"   [{idx_count}/{len(danh_sach_vong_nay)}] {ten[:50]}...")
            print(f"      📍 Tọa độ cũ: {toa_do_cu}")
            
            # Lấy tọa độ mới
            toa_do_moi, thanh_cong = lay_toa_do_chinh_xac(ten, dia_chi, quan)
            
            # Lưu checkpoint
            checkpoint_row = {
                'Index': i,
                'TenDiaDiem': ten,
                'ToaDoMoi': toa_do_moi if thanh_cong else 'FAILED',
                'TrangThai': 'PENDING'
            }
            
            if thanh_cong:
                if toa_do_moi != toa_do_cu:
                    df.at[i, 'ToaDo'] = toa_do_moi
                    print(f"      ✅ Tọa độ mới: {toa_do_moi}")
                    so_thanh_cong += 1
                    checkpoint_row['TrangThai'] = 'UPDATED'
                    
                    # Lưu vào file ngay
                    df.to_csv(FILE_INPUT, index=False, encoding='utf-8-sig')
                else:
                    print(f"      ➡️ Tọa độ không đổi")
                    so_khong_doi += 1
                    checkpoint_row['TrangThai'] = 'UNCHANGED'
            else:
                print(f"      ❌ Không tìm thấy")
                so_that_bai += 1
                checkpoint_row['TrangThai'] = 'FAILED'
            
            # Lưu checkpoint
            da_xu_ly.add(i)
            df_checkpoint_append = pd.DataFrame([checkpoint_row])
            df_checkpoint_append.to_csv(
                FILE_CHECKPOINT, 
                mode='a', 
                header=False,
                index=False, 
                encoding='utf-8-sig'
            )
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print(f"\n\n⚠️ DỪNG GIỮA CHỪNG!")
        print(f"   💾 Tiến độ đã lưu: {FILE_CHECKPOINT}")
        print(f"   🔄 Chạy lại script để RESUME")
        driver.quit()
        exit(0)
    
    # ==========================================
    # 6. KIỂM TRA SAU KHI SỬA
    # ==========================================
    print(f"\n📊 Kết quả vòng {vong_sua}:")
    print(f"   • Sửa thành công: {so_thanh_cong}")
    print(f"   • Không đổi: {so_khong_doi}")
    print(f"   • Thất bại: {so_that_bai}")
    
    print(f"\n🔍 Kiểm tra lại tọa độ sau khi sửa...")
    
    # Đọc lại file
    df = pd.read_csv(FILE_INPUT, encoding='utf-8-sig')
    nhom_trung_moi, toa_do_counts_moi = phan_tich_toa_do_trung(df)
    
    # Tìm tọa độ vẫn còn trùng > 2 lần
    toa_do_van_con_trung = {
        toa_do: indices 
        for toa_do, indices in nhom_trung_moi.items() 
        if len(indices) > 2
    }
    
    if len(toa_do_van_con_trung) > 0:
        print(f"   ⚠️ Phát hiện {len(toa_do_van_con_trung)} tọa độ vẫn trùng >2 lần:")
        
        for i, (toa_do, indices) in enumerate(list(toa_do_van_con_trung.items())[:5], 1):
            print(f"      {i}. {toa_do} - {len(indices)} quán")
            for idx in indices[:3]:
                print(f"         • {df.loc[idx, 'TenDiaDiem'][:40]}")
        
        if vong_sua < MAX_VONG:
            print(f"\n   🔄 Sẽ chạy vòng {vong_sua + 1} để sửa lại!")
            
            # Thêm vào danh sách cần sửa (bỏ quán đầu tiên mỗi nhóm)
            danh_sach_sua_them = []
            for toa_do, indices in toa_do_van_con_trung.items():
                # GIỮ quán đầu, SỬA các quán còn lại
                danh_sach_sua_them.extend(indices[1:])
            
            # Thêm vào danh sách chính (nhưng chỉ những quán chưa xử lý)
            danh_sach_can_sua.extend([idx for idx in danh_sach_sua_them if idx not in danh_sach_can_sua])
            
            print(f"   📝 Thêm {len(danh_sach_sua_them)} quán vào danh sách sửa")
            
            vong_sua += 1
        else:
            print(f"\n   ⏹️ Đã chạy {MAX_VONG} vòng, dừng lại!")
            print(f"   💡 Các tọa độ còn trùng có thể do quán thực sự nằm chung tòa nhà")
            break
    else:
        print(f"   ✅ Không còn tọa độ nào trùng >2 lần!")
        break

driver.quit()

# ==========================================
# 7. BÁO CÁO CUỐI CÙNG
# ==========================================
print(f"\n" + "="*70)
print("📊 BÁO CÁO CUỐI CÙNG")
print("="*70)

# Phân tích lần cuối
df_final = pd.read_csv(FILE_INPUT, encoding='utf-8-sig')
nhom_trung_final, toa_do_counts_final = phan_tich_toa_do_trung(df_final)

tong_quan_trung_ban_dau = sum(len(v) for v in nhom_trung.values())
tong_quan_trung_hien_tai = sum(len(v) for v in nhom_trung_final.values())

print(f"\n📈 So sánh:")
print(f"   • Tọa độ trùng:")
print(f"     - TRƯỚC: {len(nhom_trung)} tọa độ")
print(f"     - SAU:   {len(nhom_trung_final)} tọa độ")
print(f"     - Giảm:  {len(nhom_trung) - len(nhom_trung_final)} tọa độ")

print(f"\n   • Quán bị ảnh hưởng:")
print(f"     - TRƯỚC: {tong_quan_trung_ban_dau} quán")
print(f"     - SAU:   {tong_quan_trung_hien_tai} quán")
print(f"     - Giảm:  {tong_quan_trung_ban_dau - tong_quan_trung_hien_tai} quán")

if len(nhom_trung_final) > 0:
    print(f"\n⚠️ Vẫn còn {len(nhom_trung_final)} tọa độ trùng:")
    for i, (toa_do, indices) in enumerate(list(nhom_trung_final.items())[:10], 1):
        print(f"   {i}. {toa_do} - {len(indices)} quán:")
        for idx in indices[:3]:
            print(f"      • {df_final.loc[idx, 'TenDiaDiem'][:40]}")
        if len(indices) > 3:
            print(f"      ... và {len(indices) - 3} quán khác")
    
    print(f"\n💡 Lưu ý:")
    print(f"   • Có thể là quán trong cùng tòa nhà (HỢP LỆ)")
    print(f"   • Hoặc Google Maps trả về cùng tọa độ cho nhiều quán gần nhau")
else:
    print(f"\n✅ HOÀN HẢO! Không còn tọa độ trùng!")

print(f"\n📁 Files:")
print(f"   • File chính: {FILE_INPUT} (đã cập nhật)")
print(f"   • Backup: {FILE_BACKUP}")

# Xóa checkpoint nếu hoàn thành
if os.path.exists(FILE_CHECKPOINT):
    os.remove(FILE_CHECKPOINT)
    print(f"   • Checkpoint: Đã xóa (hoàn thành)")

print(f"\n" + "="*70)
print("✅ HOÀN TẤT!")
print("="*70)