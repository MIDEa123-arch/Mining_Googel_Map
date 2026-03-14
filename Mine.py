import pandas as pd
import time
import re
import urllib.parse # Thêm thư viện này để mã hóa URL
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
# 1. CẤU HÌNH ĐỊA BÀN VÀ QUOTA
# ==========================================
DANH_SACH_QUAN = [
    "Quận 1", "Quận 3", "Quận 4", "Quận 5", "Quận 6", 
    "Quận 7", "Quận 8", "Quận 10", "Quận 11", "Quận 12", 
    "Bình Thạnh", "Gò Vấp", "Phú Nhuận", "Tân Bình", "Tân Phú", 
    "Bình Tân", "Thủ Đức"
]

CAU_HINH_CHUYEN_MUC = {
    "Quán ăn": 10, "Nhà hàng": 8, "Nhà hàng gia đình": 5, "Quán ăn vỉa hè": 8,
    "Nhà hàng hải sản": 5, "Quán nướng": 8, "Nhà hàng chay": 5, "Quán phở": 5, "Quán bún bò": 5, "Nhà hàng lẩu": 8,
    "Nhà hàng Thái": 3, "Nhà hàng Hàn Quốc": 4, "Nhà hàng Nhật Bản": 4, "Nhà hàng Ý": 3, "Nhà hàng món Âu": 4,
    "Quán cà phê": 15, "Quán trà sữa": 10, "Tiệm bánh": 5, "Quán kem": 3, "Quán sinh tố": 3,
    "Quán nhậu": 10, "Quán bar": 3, "Pub": 3, "Câu lạc bộ đêm": 2, "Beer club": 3
}

SO_LUONG_REVIEW_CAN_LAY = 50 
FILE_LUU = "Data_ToanTap_AmThuc_HCM.csv"

cot_co_ban = [
    "TenDiaDiem", "NhomGoc", "Quan", "ToaDo", "DiaChi", "LoaiDiaDiem", "MucGia", "DanhGia", "SoDanhGia", 
    "GioMoCua_Thứ Hai", "GioMoCua_Thứ Ba", "GioMoCua_Thứ Tư", "GioMoCua_Thứ Năm", "GioMoCua_Thứ Sáu", "GioMoCua_Thứ Bảy", "GioMoCua_Chủ Nhật",
    "GioiThieu", "TienIch_Tags", "DanhGiaChiTiet"
]

# ==========================================
# 2. KHỞI TẠO TRÌNH DUYỆT
# ==========================================
print(f"=> KHỞI ĐỘNG CỖ MÁY CÀO (CHẾ ĐỘ ÉP TÌM BẰNG URL)...")
chrome_options = Options()
# chrome_options.add_argument("--headless=new") 
driver = webdriver.Chrome(options=chrome_options)
driver.get("https://www.google.com/maps") 
time.sleep(2)

# ==========================================
# CÁC HÀM BỔ TRỢ CHO ĐÀO DATA
# ==========================================
def cuon_het_danh_sach_quan():
    print("   -> Đang cuộn danh sách quán...")
    try:
        scrollable_div = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']"))
        )
        so_luong_truoc = 0
        so_lan_khong_thay_doi = 0
        for i in range(10):
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
            time.sleep(1.5) 
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
    for _ in range(3):
        if driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc"): 
            time.sleep(1); return
        try:
            btn_back = driver.find_element(By.CSS_SELECTOR, "button.hYBOP.FeXq4d")
            driver.execute_script("arguments[0].click();", btn_back)
            time.sleep(2) 
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.hfpxzc")))
        except: break

def lay_toa_do_tu_url(url):
    match = re.search(r'@([-+]?\d+\.\d+),([-+]?\d+\.\d+)', url)
    if match: return f"{match.group(1)}, {match.group(2)}"
    return ""

def doi_trang_quan_load_xong(timeout=10):
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.DUwDvf.lfPIob")))
        time.sleep(1.5)
        return True
    except: return False

def doi_url_thay_doi(url_cu, timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        url_hien_tai = driver.current_url
        if url_hien_tai != url_cu and "@" in url_hien_tai: return True
        time.sleep(0.3)
    return False

# ==========================================
# BƯỚC 1: KHỞI TẠO BỘ NHỚ ĐỂ CHUẨN BỊ MINE
# ==========================================
print("\n🚀 BẮT ĐẦU CRAWLER (ĐÀO DATA)...\n")
danh_sach_da_duyet = set()  
danh_sach_toa_do = set()    
danh_sach_link_di_lac = set() 
tien_do_da_cao = {} 

if not os.path.exists(FILE_LUU):
    pd.DataFrame(columns=cot_co_ban).to_csv(FILE_LUU, index=False, encoding='utf-8-sig')
else:
    try:
        df_cu = pd.read_csv(FILE_LUU)
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
        print(f"   -> Lỗi khởi tạo bộ nhớ: {e}")

# ==========================================
# VÒNG LẶP CHÍNH CỦA GIAI ĐOẠN ĐÀO DATA
# ==========================================
for nhom, max_quota_hien_tai in CAU_HINH_CHUYEN_MUC.items():
    for quan in DANH_SACH_QUAN:
        
        key_tien_do = f"{nhom}_{quan}"
        so_luong_da_luy_ke = tien_do_da_cao.get(key_tien_do, 0)
        
        if so_luong_da_luy_ke >= max_quota_hien_tai:
            print(f"\n⏭️ BỎ QUA: [{nhom} - {quan}] (Đã cào đủ {so_luong_da_luy_ke}/{max_quota_hien_tai})")
            continue

        tu_khoa = f"Danh sách {nhom} {quan} Thành phố Hồ Chí Minh"
        print(f"\n" + "="*50)
        print(f"🚀 ĐANG QUÉT: {tu_khoa} (Tiến độ: {so_luong_da_luy_ke}/{max_quota_hien_tai})")
        print("="*50)

        try:
            # =======================================================
            # ÁP DỤNG CÁCH 2: ÉP TÌM KIẾM BẰNG URL ĐỂ TRÁNH NHẢY THẲNG
            # =======================================================
            tu_khoa_url = urllib.parse.quote(tu_khoa)
            url_search = f"https://www.google.com/maps/search/{tu_khoa_url}"
            driver.get(url_search)
            
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.hfpxzc")))
            time.sleep(2)
        except Exception as e: 
            print("   -> [LAG MẠNG / KHÔNG CÓ QUÁN] Load quá 15s không thấy danh sách. Chuyển!")
            continue
        
        cuon_het_danh_sach_quan()
        
        cac_the_a_ban_dau = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
        print(f"   -> Tìm thấy {len(cac_the_a_ban_dau)} quán trong khu vực")
        
        index_quan_hien_tai = 0
        
        while index_quan_hien_tai < len(cac_the_a_ban_dau):
            if so_luong_da_luy_ke >= max_quota_hien_tai: 
                print(f"   -> Đã đủ quota {max_quota_hien_tai}, dừng!")
                break
            
            cac_the_a = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
            if index_quan_hien_tai >= len(cac_the_a): 
                print(f"   -> Hết quán để duyệt (index {index_quan_hien_tai})")
                break
            
            the_a = cac_the_a[index_quan_hien_tai]
            ten_dia_diem = str(the_a.get_attribute("aria-label")).strip()
            href_quan = str(the_a.get_attribute("href")).strip()
            
            key_check = f"{ten_dia_diem}|{quan}"
            
            if not ten_dia_diem or key_check in danh_sach_da_duyet:
                print(f"   -> [BỎ QUA - ĐÃ CÓ] {ten_dia_diem}")
                index_quan_hien_tai += 1
                continue
                
            if href_quan in danh_sach_link_di_lac:
                print(f"   -> [BỎ QUA - LINK LẠC] {ten_dia_diem}")
                index_quan_hien_tai += 1
                continue
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", the_a)
            time.sleep(0.5)
            
            url_truoc_khi_click = driver.current_url
            try:
                driver.execute_script("arguments[0].click();", the_a)
            except:
                print(f"   -> [LỖI CLICK] {ten_dia_diem}")
                index_quan_hien_tai += 1
                continue
            
            if not doi_url_thay_doi(url_truoc_khi_click, timeout=10):
                print(f"   -> https://en.bab.la/dictionary/vietnamese-english/kh%C3%B4ng-thay-%C4%91%E1%BB%95i {ten_dia_diem} - Bỏ qua")
                index_quan_hien_tai += 1
                ve_lai_danh_sach_quan()
                continue
            
            if not doi_trang_quan_load_xong(timeout=10):
                print(f"   -> [TIMEOUT] Trang quán không load. Bỏ qua.")
                index_quan_hien_tai += 1
                ve_lai_danh_sach_quan()
                continue
            
            time.sleep(1)
            
            row_data = {col: "" for col in cot_co_ban}
            row_data["TenDiaDiem"] = ten_dia_diem
            row_data["NhomGoc"] = nhom
            row_data["Quan"] = quan
            
            link_hien_tai = driver.current_url
            toa_do = lay_toa_do_tu_url(link_hien_tai)
            row_data["ToaDo"] = toa_do
            
            if toa_do and toa_do in danh_sach_toa_do:
                if key_check in danh_sach_da_duyet:
                    print(f"   -> [BỎ QUA - TRÙNG HOÀN TOÀN] {ten_dia_diem} ({toa_do})")
                    index_quan_hien_tai += 1
                    ve_lai_danh_sach_quan()
                    continue
                else:
                    print(f"   -> [CẢNH BÁO] {ten_dia_diem} có cùng tọa độ với quán khác, nhưng vẫn lấy vì tên khác")
            
            if link_hien_tai in danh_sach_link_di_lac:
                index_quan_hien_tai += 1
                ve_lai_danh_sach_quan()
                continue

            try:
                io6yte = driver.find_elements(By.CSS_SELECTOR, "div.Io6YTe.fontBodyMedium.kR99db.fdkmkc")
                if len(io6yte) >= 2: row_data["DiaChi"] = io6yte[0].get_attribute("textContent").strip()
            except: pass

            dia_chi_text = row_data["DiaChi"]
            mau_kiem_tra_quan = rf"{quan}(?!\d)" 
            
            dia_chi_text = row_data["DiaChi"]
            
            if not dia_chi_text:
                danh_sach_link_di_lac.add(href_quan)
                index_quan_hien_tai += 1
                ve_lai_danh_sach_quan()
                continue

            # Ép về chữ thường để dễ so sánh, không sợ viết hoa/viết thường
            dia_chi_lower = dia_chi_text.lower()
            
            # Check bao lô cả tiếng Anh lẫn tiếng Việt, viết tắt
            co_hcm = "hồ chí minh" in dia_chi_lower or "ho chi minh" in dia_chi_lower or "hcm" in dia_chi_lower
            
            # Check đúng tên quận (Giữ nguyên Regex cực chuẩn của bạn)
            mau_kiem_tra_quan = rf"{quan}(?!\d)" 
            dung_quan = re.search(mau_kiem_tra_quan, dia_chi_text, re.IGNORECASE)

            # Bỏ luôn việc ép phải có chữ Việt Nam/Vietnam. Chỉ cần ở HCM và đúng Quận là lụm!
            if not (co_hcm and dung_quan):
                print(f"   -> [BỎ QUA - LẠC ĐỊA BÀN] {ten_dia_diem} ({dia_chi_text})")
                danh_sach_link_di_lac.add(href_quan)
                index_quan_hien_tai += 1
                ve_lai_danh_sach_quan()
                continue

            print(f"   -> [{so_luong_da_luy_ke + 1}/{max_quota_hien_tai}] Đang lụm: {ten_dia_diem} ({toa_do})")

            try:
                the_danh_gia = driver.find_element(By.CSS_SELECTOR, "div.F7nice")
                cac_span = the_danh_gia.find_elements(By.XPATH, "./span")
                
                # Bóc điểm số (Ví dụ: 4,5)
                row_data["DanhGia"] = cac_span[0].find_element(By.XPATH, ".//span[@aria-hidden='true']").get_attribute("textContent").strip()
                
                # Bóc text thô của số lượng đánh giá (Bất chấp tiếng Anh/Việt, nó sẽ lấy ra "(1.244)")
                chuoi_so_luong = cac_span[1].get_attribute("textContent").strip()
                
                # Dùng Regex vứt hết dấu ngoặc, dấu chấm, chữ cái... chỉ giữ lại đúng con số
                so_luong_thuc_te = re.sub(r'\D', '', chuoi_so_luong)
                
                if so_luong_thuc_te:
                    row_data["SoDanhGia"] = int(so_luong_thuc_te)
                else:
                    row_data["SoDanhGia"] = 0
            except: 
                pass
                
            if not row_data.get("SoDanhGia") or row_data["SoDanhGia"] <= 10:
                print(f"      -> [BỎ QUA] Không đủ 10 đánh giá.")
                danh_sach_link_di_lac.add(href_quan)
                index_quan_hien_tai += 1
                ve_lai_danh_sach_quan()
                continue
                
            try: row_data["LoaiDiaDiem"] = driver.find_element(By.CSS_SELECTOR, "button.DkEaL").get_attribute("textContent").strip()
            except: pass
                
            try: row_data["MucGia"] = driver.find_element(By.CSS_SELECTOR, "div.MNVeJb.eXOdV").text.split('\n')[0].strip()
            except: pass

            try:
                cac_the_tr = driver.find_elements(By.CSS_SELECTOR, "tr.y0skZc")
                for tr in cac_the_tr:
                    thu = tr.find_element(By.CSS_SELECTOR, "td.ylH6lf").get_attribute("textContent").strip()
                    gio = tr.find_element(By.CSS_SELECTOR, "td.mxowUb").get_attribute("textContent").strip()
                    if f"GioMoCua_{thu}" in row_data: row_data[f"GioMoCua_{thu}"] = gio
            except: pass

            try:
                tab_gioi_thieu = driver.find_element(By.XPATH, "//button[@role='tab' and contains(@aria-label, 'Giới thiệu')]")
                driver.execute_script("arguments[0].click();", tab_gioi_thieu)
                time.sleep(1) 
                try: row_data["GioiThieu"] = driver.find_element(By.CSS_SELECTOR, "span.HlvSq").get_attribute("textContent").strip()
                except: pass

                try:
                    cac_the_li = driver.find_elements(By.CSS_SELECTOR, "div.iP2t7d.fontBodyMedium li.hpLkke")
                    tat_ca_tags = []
                    for li in cac_the_li:
                        text_item = li.find_element(By.CSS_SELECTOR, "span[aria-label]").get_attribute("textContent").strip()
                        try:
                            icon = li.find_element(By.CSS_SELECTOR, "span.google-symbols").get_attribute("textContent").strip()
                            trang_thai = "(ko có)" if "" in icon else "(có)"
                        except: trang_thai = "(có)"
                        tat_ca_tags.append(f"{text_item} {trang_thai}")
                    if tat_ca_tags: row_data["TienIch_Tags"] = " | ".join(tat_ca_tags)
                except: pass
            except: pass

            try:
                tab_danh_gia = driver.find_element(By.XPATH, "//button[@role='tab' and contains(@aria-label, 'Bài đánh giá')]")
                driver.execute_script("arguments[0].click();", tab_danh_gia)
                time.sleep(1.5) 

                so_luong_hien_tai = 0
                so_lan_scroll_khong_tang = 0
                
                while so_luong_hien_tai < SO_LUONG_REVIEW_CAN_LAY and so_lan_scroll_khong_tang < 5:
                    cac_khoi_review = driver.find_elements(By.CSS_SELECTOR, "div.jftiEf")
                    so_luong_moi = len(cac_khoi_review)
                    
                    if so_luong_moi >= SO_LUONG_REVIEW_CAN_LAY: break
                    if so_luong_moi == so_luong_hien_tai: so_lan_scroll_khong_tang += 1
                    else: so_lan_scroll_khong_tang = 0
                        
                    so_luong_hien_tai = so_luong_moi
                    driver.execute_script("var s = document.querySelectorAll('.kA9KIf'); for(var i=0; i<s.length; i++) s[i].scrollTop = s[i].scrollHeight;")
                    time.sleep(1) 

                driver.execute_script("""
                    let reviewBlocks = document.querySelectorAll('div.jftiEf');
                    reviewBlocks.forEach(block => {
                        let btns = block.querySelectorAll('button');
                        btns.forEach(b => {
                            let text = b.innerText.trim().toLowerCase();
                            if(text === 'xem thêm' || text === 'thêm' || text === 'more') { b.click(); }
                        });
                    });
                """)
                time.sleep(1.5) 

                driver.execute_script("""
                    let reviewBlocks = document.querySelectorAll('div.jftiEf');
                    reviewBlocks.forEach(block => {
                        let btns = block.querySelectorAll('button');
                        btns.forEach(b => {
                            let text = b.innerText.trim().toLowerCase();
                            if(text.includes('xem bản dịch') || text.includes('translate')) { b.click(); }
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
                        except: sao = "? sao"
                        if ten and noi_dung: danh_sach_review_text.append(f"[{ten} - {sao}]: {noi_dung}")
                    except: pass
                
                if danh_sach_review_text:
                    row_data["DanhGiaChiTiet"] = " \n---\n ".join(danh_sach_review_text)
                    print(f"      -> Đã bóc & ép dịch được {len(danh_sach_review_text)} bài đánh giá!")
            except: print("      -> (Mẹo: Quán này không có tab đánh giá)")
            
            danh_sach_da_duyet.add(key_check)
            if toa_do: danh_sach_toa_do.add(toa_do)
            
            df_row = pd.DataFrame([row_data])
            df_row.to_csv(FILE_LUU, mode='a', header=not os.path.exists(FILE_LUU), index=False, encoding='utf-8-sig')
                
            so_luong_da_luy_ke += 1
            tien_do_da_cao[key_tien_do] = so_luong_da_luy_ke
            print(f"   -> [🎉 XONG] Đã lưu thông tin: {ten_dia_diem}")
            
            index_quan_hien_tai += 1
            ve_lai_danh_sach_quan()

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