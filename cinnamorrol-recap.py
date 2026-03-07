import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import time
from streamlit_webrtc import webrtc_streamer
import cv2
import numpy as np
from pyzbar.pyzbar import decode

# --- CONFIG ---
st.set_page_config(page_title="Wahana Auto-Scan", layout="wide")

# --- SESSION STATE (Agar Tanggal & Data Aman) ---
if 'recap_date' not in st.session_state:
    st.session_state['recap_date'] = datetime.now()
if 'last_code' not in st.session_state:
    st.session_state['last_code'] = ""

# --- KONEKSI ---
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
        st.error(f"Koneksi Gagal: {e}")
        return None

sh = init_gsheet()

# --- FUNGSI SIMPAN ---
def auto_save(barcode_val):
    if not barcode_val or barcode_val == st.session_state['last_code']:
        return
    
    try:
        sheet_recap = sh.worksheet("Report Recap")
        ts = datetime.now().strftime("%H:%M:%S")
        
        # Cek Duplikat
        all_val = sheet_recap.col_values(2)
        if barcode_val in all_val:
            st.warning(f"⚠️ {barcode_val} sudah ada!")
            st.session_state['last_code'] = barcode_val
            return

        # Simpan ke Master (Kolom B & C)
        next_r = len(all_val) + 1
        sheet_recap.update_acell(f'B{next_r}', barcode_val)
        sheet_recap.update_acell(f'C{next_r}', ts)
        
        st.session_state['last_code'] = barcode_val
        st.success(f"✅ Tersimpan: {barcode_val}")
        time.sleep(0.5)
        st.rerun()
    except Exception as e:
        st.error(f"Gagal simpan: {e}")

# --- UI ---
st.title("☁️ WAHANA REAL-TIME SCANNER")

col_cam, col_tab = st.columns([1, 1])

with col_cam:
    st.session_state['recap_date'] = st.date_input("📅 Tanggal", value=st.session_state['recap_date'])
    
    # SCANNER WEBRTC
    def video_frame_callback(frame):
        img = frame.to_ndarray(format="bgr24")
        detected_barcodes = decode(img)
        
        for barcode in detected_barcodes:
            data = barcode.data.decode('utf-8')
            # Kirim data ke session state untuk diproses di luar thread video
            st.session_state['detected_now'] = data
            # Gambar kotak tanda scan berhasil
            pts = np.array([barcode.polygon], np.int32)
            cv2.polylines(img, [pts], True, (0, 255, 0), 3)
            
        return frame.from_ndarray(img, format="bgr24")

    webrtc_streamer(
        key="wahana-scan",
        video_frame_callback=video_frame_callback,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": True, "audio": False}
    )

    # Proses hasil deteksi
    if 'detected_now' in st.session_state:
        auto_save(st.session_state['detected_now'])
        del st.session_state['detected_now']

with col_tab:
    st.subheader("📊 Data Terbaru")
    if sh:
        ws = sh.worksheet("Report Recap")
        res = ws.get_all_values()
        if len(res) > 1:
            df = pd.DataFrame(res[1:], columns=["No", "Barcode", "Jam"])
            # Tampilkan 15 data terbaru di posisi atas
            st.table(df.iloc[::-1].head(15))

st.caption("v4.1 - Auto Enter & No-Click Scanner")
