import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Wahana Recap", page_icon="📸", layout="wide")

# --- INISIALISASI SESSION STATE ---
if 'recap_date' not in st.session_state:
    st.session_state['recap_date'] = datetime.now()
if 'last_scan' not in st.session_state:
    st.session_state['last_scan'] = ""

# --- CUSTOM CSS: BLUE GLOSSY CRYSTAL ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0ea5e9 0%, #38bdf8 30%, #e0f2fe 100%);
        background-attachment: fixed;
    }
    .main-title {
        color: #000000; font-family: 'Segoe UI'; font-weight: 900;
        text-align: center; font-size: 3rem; text-transform: uppercase;
    }
    div[data-testid="stForm"], .glossy-card {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(20px);
        border-radius: 30px; border: 1px solid rgba(255, 255, 255, 0.4);
        padding: 20px; color: #000000;
    }
    /* Tombol Scanner Gaya Modern */
    .stCameraInput > label { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- KONEKSI GSHEET ---
@st.cache_resource
def init_gsheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        url = "https://docs.google.com/spreadsheets/d/1vlwLdTxPLDnDkrn4luNKnRr_SH5TG-YJXK5NZAdWCVQ/edit?usp=sharing"
        return client.open_by_url(url)
    except Exception as e:
        st.error(f"Koneksi Cloud Terputus: {e}")
        return None

sh = init_gsheet()

def save_to_gsheet(barcode_data, date_obj):
    """Fungsi helper untuk simpan data agar bisa dipanggil otomatis"""
    try:
        sheet_recap = sh.worksheet("Report Recap")
        ts = datetime.now().strftime("%H:%M:%S")
        sheet_daily_name = date_obj.strftime("%d_%m_%Y_Rekap Wahana")
        
        # Anti-Duplikat
        all_b_values = sheet_recap.col_values(2)[1:1340]
        if barcode_data in all_b_values:
            return "duplicate", barcode_data
        
        # Update Main Recap
        next_row = len(sheet_recap.col_values(2)) + 1
        sheet_recap.update_acell(f'B{next_row}', barcode_data)
        sheet_recap.update_acell(f'C{next_row}', ts)
        
        # Update Daily Sheet
        try:
            ws_daily = sh.worksheet(sheet_daily_name)
        except gspread.WorksheetNotFound:
            ws_daily = sh.add_worksheet(title=sheet_daily_name, rows="1000", cols="5")
            ws_daily.append_row(["Data Barcode", "Timestamp"])
        
        ws_daily.append_row([barcode_data, ts])
        return "success", barcode_data
    except Exception as e:
        return "error", str(e)

if sh:
    st.markdown("<h1 class='main-title'>📸 SCANNER WAHANA</h1>", unsafe_allow_html=True)
    
    # --- BAGIAN SCANNER OTOMATIS ---
    with st.container():
        st.markdown("### 📱 Camera QR Scanner")
        # Menggunakan camera_input sebagai trigger otomatis
        img_file = st.camera_input("Arahkan QR Code ke Kamera")
        
        if img_file:
            # Di dunia nyata, browser akan menangkap gambar. 
            # Untuk 'Auto Enter' Barcode, kita asumsikan input dari Honeywell tetap ada
            # Namun jika ingin Full Camera QR, kita butuh library 'pyzbar' atau 'opencv'
            import cv2
            import numpy as np
            
            file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
            opencv_img = cv2.imdecode(file_bytes, 1)
            detector = cv2.QRCodeDetector()
            data, points, _ = detector.detectAndDecode(opencv_img)
            
            if data:
                if data != st.session_state['last_scan']:
                    status, msg = save_to_gsheet(data, st.session_state['recap_date'])
                    st.session_state['last_scan'] = data # Cegah loop simpan
                    
                    if status == "success":
                        st.toast(f"Tersimpan: {data}", icon="✅")
                        st.success(f"Data {data} Berhasil Masuk!")
                        time.sleep(1)
                        st.rerun()
                    elif status == "duplicate":
                        st.warning(f"Data {data} sudah ada!")
            else:
                st.info("QR Code tidak terdeteksi. Pastikan gambar jelas.")

    # --- INPUT MANUAL (TETAP TERSEDIA) ---
    with st.expander("⌨️ Input Manual / Honeywell Scan"):
        with st.form("manual_form", clear_on_submit=True):
            date_pick = st.date_input("Tanggal", value=st.session_state['recap_date'])
            st.session_state['recap_date'] = date_pick
            manual_barcode = st.text_input("Barcode Value")
            submit_manual = st.form_submit_button("Simpan Manual")
            
            if submit_manual and manual_barcode:
                status, msg = save_to_gsheet(manual_barcode, date_pick)
                if status == "success":
                    st.success("Data Tersimpan!")
                    st.rerun()

    # --- MINI MONITOR (REVERSED) ---
    st.markdown("---")
    st.markdown("### 📊 Live Monitor")
    
    sheet_recap = sh.worksheet("Report Recap")
    raw_data = sheet_recap.get_all_values()
    
    if len(raw_data) > 1:
        df = pd.DataFrame(raw_data[1:], columns=["No", "Data Barcode", "Timestamp"])
        df_view = df.iloc[::-1].head(10) # Tampilkan 10 terbaru
        st.table(df_view) # Table lebih ringan untuk mobile
    else:
        st.info("Belum ada data.")

st.caption("Cinnamoroll Wahana System v3.0 - Auto Camera Mode")
