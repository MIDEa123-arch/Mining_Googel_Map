import pandas as pd
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

# ==========================================
# 1. CẤU HÌNH ĐỊA BÀN (FULL 19 QUẬN NỘI THÀNH HCM)
# ==========================================
DANH_SACH_QUAN = [
    "Quận 1", "Quận 3", "Quận 4", "Quận 5", "Quận 6", 
    "Quận 7", "Quận 8", "Quận 10", "Quận 11", "Quận 12", 
    "Bình Thạnh", "Gò Vấp", "Phú Nhuận", "Tân Bình", "Tân Phú", 
    "Bình Tân", "Thủ Đức"
]

# ==========================================
# 2. CẤU HÌNH QUOTA CÀY CUỐC SỐ LƯỢNG LỚN
# ==========================================
CAU_HINH_CHUYEN_MUC = {
    # --- Nhóm 1: Đồ ăn cơ bản ---
    "Quán ăn": 10, "Nhà hàng": 8, "Nhà hàng gia đình": 5, "Quán ăn vỉa hè": 8,
    
    # --- Nhóm 2: Chuyên đề món ăn ---
    "Nhà hàng hải sản": 5, "Quán nướng": 8, "Nhà hàng chay": 5, "Quán phở": 5, "Quán bún bò": 5, "Nhà hàng lẩu": 8,
    
    # --- Nhóm 3: Quốc tế ---
    "Nhà hàng Thái": 3, "Nhà hàng Hàn Quốc": 4, "Nhà hàng Nhật Bản": 4, "Nhà hàng Ý": 3, "Nhà hàng món Âu": 4,
    
    # --- Nhóm 4: Đồ uống & Tráng miệng ---
    "Quán cà phê": 15, "Quán trà sữa": 10, "Tiệm bánh": 5, "Quán kem": 3, "Quán sinh tố": 3,
    
    # --- Nhóm 5: Nightlife (Ăn chơi về đêm) ---
    "Quán nhậu": 10, "Quán bar": 3, "Pub": 3, "Câu lạc bộ đêm": 2, "Beer club": 3
}

SO_LUONG_REVIEW_CAN_LAY = 50 
FILE_LUU = "Data_ToanTap_AmThuc_HCM.csv"

# ==========================================
# 3. KHỞI TẠO CỔ MÁY VÀ BỘ NHỚ
# ==========================================
print(f"=> KHỞI ĐỘNG CỖ MÁY CÀO (FULL QUẬN + BỘ NHỚ + BUNG MỞ TOÀN BỘ REVIEW DÀI)...")
chrome_options = Options()
# Bỏ comment dòng dưới nếu muốn chạy ngầm
# chrome_options.add_argument("--headless=new") 
driver = webdriver.Chrome(options=chrome_options)

cot_co_ban = [
    "TenDiaDiem", "NhomGoc", "Quan", "ToaDo", "DiaChi", "LoaiDiaDiem", "MucGia", "DanhGia", "SoDanhGia", 
    "GioMoCua_Thứ Hai", "GioMoCua_Thứ Ba", "GioMoCua_Thứ Tư", "GioMoCua_Thứ Năm", "GioMoCua_Thứ Sáu", "GioMoCua_Thứ Bảy", "GioMoCua_Chủ Nhật",
    "GioiThieu", "TienIch_Tags", "DanhGiaChiTiet"
]

# ==========================================
# FIX: TĂNG CƯỜNG BỘ NHỚ - CHECK TRÙNG BẰNG TÊN + QUẬN + TỌA ĐỘ
# ==========================================
danh_sach_da_duyet = set()  # Lưu key dạng "TenDiaDiem|Quan"
danh_sach_toa_do = set()    # Lưu tọa độ để tránh trùng
danh_sach_link_di_lac = set() 
tien_do_da_cao = {} 

if not os.path.exists(FILE_LUU):
    pd.DataFrame(columns=cot_co_ban).to_csv(FILE_LUU, index=False, encoding='utf-8-sig')
else:
    try:
        df_cu = pd.read_csv(FILE_LUU)
        # Load danh sách đã duyệt với key phức hợp
        for _, row in df_cu.iterrows():
            if pd.notna(row.get('TenDiaDiem')) and pd.notna(row.get('Quan')):
                key = f"{row['TenDiaDiem']}|{row['Quan']}"
                danh_sach_da_duyet.add(key)
            if pd.notna(row.get('ToaDo')):
                danh_sach_toa_do.add(row['ToaDo'])
        
        if not df_cu.empty and 'NhomGoc' in df_cu.columns and 'Quan' in df_cu.columns:
            tien_do_df = df_cu.groupby(['NhomGoc', 'Quan']).size().reset_index(name='Count')
            for index, row in tien_do_df.iterrows():
                key = f"{row['NhomGoc']}_{row['Quan']}"
                tien_do_da_cao[key] = row['Count']
    except Exception as e: 
        print(f"   -> Cảnh báo khi load file cũ: {e}")

# ==========================================
# HÀM BỔ TRỢ
# ==========================================
def cuon_het_danh_sach_quan():
    """FIX: Cuộn và đợi đủ lâu để load thêm quán"""
    print("   -> Đang cuộn danh sách quán...")
    try:
        scrollable_div = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']"))
        )
        
        so_luong_truoc = 0
        so_lan_khong_thay_doi = 0
        
        # FIX: Scroll cho đến khi không còn quán mới hoặc scroll 10 lần
        for i in range(10):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
            time.sleep(1.5)  # Tăng thời gian chờ
            
            # Đếm số lượng quán hiện tại
            cac_the_a = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
            so_luong_hien_tai = len(cac_the_a)
            
            if so_luong_hien_tai == so_luong_truoc:
                so_lan_khong_thay_doi += 1
                if so_lan_khong_thay_doi >= 3:
                    print(f"      -> Đã load hết, tổng {so_luong_hien_tai} quán")
                    break
            else:
                so_lan_khong_thay_doi = 0
            
            so_luong_truoc = so_luong_hien_tai
            
    except Exception as e:
        print(f"      -> Lỗi khi cuộn: {e}")

def ve_lai_danh_sach_quan():
    """FIX: Đảm bảo quay về đúng danh sách và đợi load xong"""
    for _ in range(3):
        # Check xem đã ở danh sách chưa
        if driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc"): 
            time.sleep(1)  # Đợi thêm 1 giây để ổn định
            return
        try:
            btn_back = driver.find_element(By.CSS_SELECTOR, "button.hYBOP.FeXq4d")
            driver.execute_script("arguments[0].click();", btn_back)
            time.sleep(2)  # FIX: Tăng thời gian chờ sau khi bấm back
            
            # Đợi danh sách quán hiện ra
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.hfpxzc"))
            )
        except: 
            break

def lay_toa_do_tu_url(url):
    match = re.search(r'@([-+]?\d+\.\d+),([-+]?\d+\.\d+)', url)
    if match: return f"{match.group(1)}, {match.group(2)}"
    return ""

def doi_trang_quan_load_xong(timeout=10):
    """FIX MỚI: Hàm đợi trang quán mới load xong hoàn toàn"""
    try:
        # Đợi tên quán xuất hiện
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.DUwDvf.lfPIob"))
        )
        time.sleep(1.5)  # Thêm buffer time để các element khác load
        return True
    except:
        return False

# ==========================================
# BẮT ĐẦU CHẠY CHÍNH
# ==========================================
driver.get("https://www.google.com/maps?hl=vi") 
time.sleep(2)

for nhom, max_quota_hien_tai in CAU_HINH_CHUYEN_MUC.items():
    for quan in DANH_SACH_QUAN:
        
        # --- KIỂM TRA BỘ NHỚ TRƯỚC KHI TÌM KIẾM ---
        key_tien_do = f"{nhom}_{quan}"
        so_luong_da_luy_ke = tien_do_da_cao.get(key_tien_do, 0)
        
        if so_luong_da_luy_ke >= max_quota_hien_tai:
            print(f"\n⏭️ BỎ QUA: [{nhom} - {quan}] (Đã cào đủ {so_luong_da_luy_ke}/{max_quota_hien_tai})")
            continue

        tu_khoa = f"{nhom} {quan} Thành phố Hồ Chí Minh"
        print(f"\n" + "="*50)
        print(f"🚀 ĐANG QUÉT: {tu_khoa} (Tiến độ: {so_luong_da_luy_ke}/{max_quota_hien_tai})")
        print("="*50)

        try:
            search_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "q")))
            search_box.clear()
            search_box.send_keys(tu_khoa)
            search_box.send_keys(Keys.ENTER)
            
            # Đợi danh sách quán hiện ra
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.hfpxzc")))
            time.sleep(2)  # FIX: Tăng thời gian chờ
            
        except Exception as e: 
            print("   -> [LAG MẠNG / KHÔNG CÓ QUÁN] Load quá 15s không thấy danh sách. Chuyển!")
            continue
        
        # FIX: Cuộn kỹ hơn để load hết quán
        cuon_het_danh_sach_quan()
        
        # Lấy tất cả các link quán sau khi scroll xong
        cac_the_a_ban_dau = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
        print(f"   -> Tìm thấy {len(cac_the_a_ban_dau)} quán trong khu vực")
        
        index_quan_hien_tai = 0
        
        while index_quan_hien_tai < len(cac_the_a_ban_dau):
            if so_luong_da_luy_ke >= max_quota_hien_tai: 
                print(f"   -> Đã đủ quota {max_quota_hien_tai}, dừng!")
                break
            
            # FIX: Re-query lại danh sách để tránh stale element
            cac_the_a = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
            
            if index_quan_hien_tai >= len(cac_the_a): 
                print(f"   -> Hết quán để duyệt (index {index_quan_hien_tai})")
                break
            
            the_a = cac_the_a[index_quan_hien_tai]
            ten_dia_diem = str(the_a.get_attribute("aria-label")).strip()
            href_quan = str(the_a.get_attribute("href")).strip()
            
            # FIX: Check trùng bằng cả tên + quận
            key_check = f"{ten_dia_diem}|{quan}"
            
            if not ten_dia_diem or key_check in danh_sach_da_duyet:
                print(f"   -> [BỎ QUA - ĐÃ CÓ] {ten_dia_diem}")
                index_quan_hien_tai += 1
                continue
                
            if href_quan in danh_sach_link_di_lac:
                print(f"   -> [BỎ QUA - LINK LẠC] {ten_dia_diem}")
                index_quan_hien_tai += 1
                continue
            
            # Scroll quán vào view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", the_a)
            time.sleep(0.5)
            
            # Click vào quán
            try:
                driver.execute_script("arguments[0].click();", the_a)
            except:
                print(f"   -> [LỖI CLICK] {ten_dia_diem}")
                index_quan_hien_tai += 1
                continue
            
            # FIX QUAN TRỌNG: Đợi trang quán MỚI load xong hoàn toàn
            if not doi_trang_quan_load_xong(timeout=10):
                print(f"   -> [TIMEOUT] Trang quán không load. Bỏ qua.")
                index_quan_hien_tai += 1
                ve_lai_danh_sach_quan()
                continue
            
            # Khởi tạo dữ liệu mới
            row_data = {col: "" for col in cot_co_ban}
            row_data["TenDiaDiem"] = ten_dia_diem
            row_data["NhomGoc"] = nhom
            row_data["Quan"] = quan
            
            # Lấy tọa độ từ URL hiện tại
            link_hien_tai = driver.current_url
            toa_do = lay_toa_do_tu_url(link_hien_tai)
            row_data["ToaDo"] = toa_do
            
            # FIX: Check trùng theo tọa độ
            if toa_do and toa_do in danh_sach_toa_do:
                print(f"   -> [BỎ QUA - TRÙNG TỌA ĐỘ] {ten_dia_diem} ({toa_do})")
                danh_sach_da_duyet.add(key_check)
                index_quan_hien_tai += 1
                ve_lai_danh_sach_quan()
                continue
            
            if link_hien_tai in danh_sach_link_di_lac:
                index_quan_hien_tai += 1
                ve_lai_danh_sach_quan()
                continue

            # Lấy địa chỉ
            try:
                io6yte = driver.find_elements(By.CSS_SELECTOR, "div.Io6YTe.fontBodyMedium.kR99db.fdkmkc")
                if len(io6yte) >= 2: 
                    row_data["DiaChi"] = io6yte[0].get_attribute("textContent").strip()
            except: 
                pass

            dia_chi_text = row_data["DiaChi"]
            mau_kiem_tra_quan = rf"{quan}(?!\d)" 
            
            # Kiểm tra địa chỉ có đúng quận không
            if not dia_chi_text or "Hồ Chí Minh" not in dia_chi_text or "Việt Nam" not in dia_chi_text or not re.search(mau_kiem_tra_quan, dia_chi_text, re.IGNORECASE):
                print(f"   -> [BỎ QUA - LẠC ĐỊA BÀN] {ten_dia_diem} ({dia_chi_text})")
                danh_sach_link_di_lac.add(href_quan)
                index_quan_hien_tai += 1
                ve_lai_danh_sach_quan()
                continue 

            print(f"   -> [{so_luong_da_luy_ke + 1}/{max_quota_hien_tai}] Đang lụm: {ten_dia_diem} ({toa_do})")

            # --- LỤM THÔNG TIN CƠ BẢN ---
            try:
                the_danh_gia = driver.find_element(By.CSS_SELECTOR, "div.F7nice")
                cac_span = the_danh_gia.find_elements(By.XPATH, "./span")
                row_data["DanhGia"] = cac_span[0].find_element(By.XPATH, ".//span[@aria-hidden='true']").text.strip()
                chuoi_so_luong = cac_span[1].find_element(By.XPATH, ".//span[contains(@aria-label, 'đánh giá')]").text.strip()
                row_data["SoDanhGia"] = int(re.sub(r'\D', '', chuoi_so_luong))
            except: 
                pass
                
            if not row_data.get("SoDanhGia") or row_data["SoDanhGia"] <= 10:
                print(f"      -> [BỎ QUA] Không đủ 10 đánh giá.")
                danh_sach_link_di_lac.add(href_quan)
                index_quan_hien_tai += 1
                ve_lai_danh_sach_quan()
                continue
                
            try: 
                row_data["LoaiDiaDiem"] = driver.find_element(By.CSS_SELECTOR, "button.DkEaL").get_attribute("textContent").strip()
            except: 
                pass
                
            try: 
                row_data["MucGia"] = driver.find_element(By.CSS_SELECTOR, "div.MNVeJb.eXOdV").text.split('\n')[0].strip()
            except: 
                pass

            # Giờ mở cửa
            try:
                cac_the_tr = driver.find_elements(By.CSS_SELECTOR, "tr.y0skZc")
                for tr in cac_the_tr:
                    thu = tr.find_element(By.CSS_SELECTOR, "td.ylH6lf").get_attribute("textContent").strip()
                    gio = tr.find_element(By.CSS_SELECTOR, "td.mxowUb").get_attribute("textContent").strip()
                    if f"GioMoCua_{thu}" in row_data: 
                        row_data[f"GioMoCua_{thu}"] = gio
            except: 
                pass

            # --- TAB GIỚI THIỆU ---
            try:
                tab_gioi_thieu = driver.find_element(By.XPATH, "//button[@role='tab' and contains(@aria-label, 'Giới thiệu')]")
                driver.execute_script("arguments[0].click();", tab_gioi_thieu)
                time.sleep(1)  # FIX: Tăng thời gian chờ
                
                try: 
                    row_data["GioiThieu"] = driver.find_element(By.CSS_SELECTOR, "span.HlvSq").get_attribute("textContent").strip()
                except: 
                    pass

                try:
                    cac_the_li = driver.find_elements(By.CSS_SELECTOR, "div.iP2t7d.fontBodyMedium li.hpLkke")
                    tat_ca_tags = []
                    for li in cac_the_li:
                        text_item = li.find_element(By.CSS_SELECTOR, "span[aria-label]").get_attribute("textContent").strip()
                        try:
                            icon = li.find_element(By.CSS_SELECTOR, "span.google-symbols").get_attribute("textContent").strip()
                            trang_thai = "(ko có)" if "" in icon else "(có)"
                        except:
                            trang_thai = "(có)"
                        tat_ca_tags.append(f"{text_item} {trang_thai}")
                    if tat_ca_tags:
                        row_data["TienIch_Tags"] = " | ".join(tat_ca_tags)
                except: 
                    pass
            except: 
                pass

            # --- TAB BÀI ĐÁNH GIÁ ---
            try:
                tab_danh_gia = driver.find_element(By.XPATH, "//button[@role='tab' and contains(@aria-label, 'Bài đánh giá')]")
                driver.execute_script("arguments[0].click();", tab_danh_gia)
                time.sleep(1.5)  # FIX: Tăng thời gian chờ

                so_luong_hien_tai = 0
                so_lan_scroll_khong_tang = 0
                
                while so_luong_hien_tai < SO_LUONG_REVIEW_CAN_LAY and so_lan_scroll_khong_tang < 5:
                    cac_khoi_review = driver.find_elements(By.CSS_SELECTOR, "div.jftiEf")
                    so_luong_moi = len(cac_khoi_review)
                    
                    if so_luong_moi >= SO_LUONG_REVIEW_CAN_LAY: break
                    if so_luong_moi == so_luong_hien_tai: 
                        so_lan_scroll_khong_tang += 1
                    else: 
                        so_lan_scroll_khong_tang = 0
                        
                    so_luong_hien_tai = so_luong_moi
                    
                    driver.execute_script("var s = document.querySelectorAll('.kA9KIf'); for(var i=0; i<s.length; i++) s[i].scrollTop = s[i].scrollHeight;")
                    time.sleep(1)  # FIX: Tăng thời gian chờ

                # Bấm nút "Xem thêm" trong review
                driver.execute_script("""
                    let reviewBlocks = document.querySelectorAll('div.jftiEf');
                    reviewBlocks.forEach(block => {
                        let btns = block.querySelectorAll('button');
                        btns.forEach(b => {
                            let text = b.innerText.trim().toLowerCase();
                            if(text === 'xem thêm' || text === 'thêm' || text === 'more') {
                                b.click();
                            }
                        });
                    });
                """)
                time.sleep(1.5)  # FIX: Tăng thời gian chờ

                # Bấm nút dịch
                driver.execute_script("""
                    let reviewBlocks = document.querySelectorAll('div.jftiEf');
                    reviewBlocks.forEach(block => {
                        let btns = block.querySelectorAll('button');
                        btns.forEach(b => {
                            let text = b.innerText.trim().toLowerCase();
                            if(text.includes('xem bản dịch') || text.includes('translate')) {
                                b.click();
                            }
                        });
                    });
                """)
                time.sleep(2) 

                cac_khoi_review = driver.find_elements(By.CSS_SELECTOR, "div.jftiEf")[:SO_LUONG_REVIEW_CAN_LAY]
                danh_sach_review_text = []
                
                for khoi in cac_khoi_review:
                    try:
                        ten = khoi.find_element(By.CSS_SELECTOR, "div.d4r55").text.strip()
                        noi_dung = khoi.find_element(By.CSS_SELECTOR, "span.wiI7pd").text.strip()
                        try:
                            sao_text = khoi.find_element(By.CSS_SELECTOR, "span.kvMYJc").get_attribute("aria-label")
                            sao = re.sub(r'\D', '', sao_text) + " sao" if sao_text else "? sao"
                        except: 
                            sao = "? sao"
                        if ten and noi_dung:
                            danh_sach_review_text.append(f"[{ten} - {sao}]: {noi_dung}")
                    except: 
                        pass
                
                if danh_sach_review_text:
                    row_data["DanhGiaChiTiet"] = " \n---\n ".join(danh_sach_review_text)
                    print(f"      -> Đã bóc & ép dịch được {len(danh_sach_review_text)} bài đánh giá!")
            except: 
                print("      -> (Mẹo: Quán này không có tab đánh giá)")
            
            # --- LƯU DỮ LIỆU ---
            danh_sach_da_duyet.add(key_check)
            if toa_do:
                danh_sach_toa_do.add(toa_do)
            
            df_row = pd.DataFrame([row_data])
            df_row.to_csv(FILE_LUU, mode='a', header=not os.path.exists(FILE_LUU), index=False, encoding='utf-8-sig')
                
            so_luong_da_luy_ke += 1
            tien_do_da_cao[key_tien_do] = so_luong_da_luy_ke
            print(f"   -> [🎉 XONG] Đã lưu thông tin: {ten_dia_diem}")
            
            # Quay lại danh sách
            index_quan_hien_tai += 1
            ve_lai_danh_sach_quan()

        # Kiểm tra đã đủ quota chưa
        if so_luong_da_luy_ke >= max_quota_hien_tai:
            print(f"   -> ✅ Đã đủ quota {max_quota_hien_tai} cho [{nhom} - {quan}]")
            continue

driver.quit()

print(f"\n=> 🧹 Đang dọn dẹp Data...")
try:
    df_final = pd.read_csv(FILE_LUU)
    so_dong_truoc = len(df_final)
    df_final['LoaiDiaDiem'] = df_final['LoaiDiaDiem'].replace(r'^\s*$', pd.NA, regex=True)
    df_final.dropna(subset=['LoaiDiaDiem'], inplace=True)
    df_final.drop_duplicates(subset=['TenDiaDiem', 'Quan'], inplace=True)
    df_final.to_csv(FILE_LUU, index=False, encoding='utf-8-sig')
    so_dong_sau = len(df_final)
    print(f"   -> Đã xóa {so_dong_truoc - so_dong_sau} dòng rác/trùng.")
    print(f"✅ ĐÃ HOÀN TẤT CHIẾN DỊCH! File sạch đẹp đã ra lò: {FILE_LUU}")
except Exception as e:
    print("   -> Lỗi khi dọn dẹp file:", e)