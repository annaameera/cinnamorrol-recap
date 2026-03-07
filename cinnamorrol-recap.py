import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import time
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
from pyzbar.pyzbar import decode
import cv2
import numpy as np

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Wahana Recap", page_icon="⚡", layout="wide")

# --- SESSION STATE ---
if 'recap_date' not in st.session_state:
    st.session_state['recap_date'] = datetime.now()
if 'last_detected' not in st.session_state:
    st.session_state['last_detected'] = None

# --- CSS GLOSSY ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0ea5e9 0%, #e0f2fe 100%); }
    .main-title { color: #000; font-weight: 900; text-align: center; font-size: 2.5rem; }
    div[data-testid="stExpander"] { background: rgba(255,255,255,0.2); border-radius: 20px; }
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
        st.error(f"Koneksi Gagal: {e}")
        return None

sh = init_gsheet()

# --- LOGIKA SIMPAN DATA ---
def push_data(barcode_val):
    try:
        sheet_recap = sh.worksheet("Report Recap")
        ts = datetime.now().strftime("%H:%M:%S")
        date_str = st.session_state['recap_date'].strftime("%d_%m_%Y_Rekap Wahana")
        
        # Cek Duplikat di kolom B
        existing = sheet_recap.col_values(2)
        if barcode_val in existing:
            return False, "Duplikat"

        # Simpan ke Master Recap
        next_row = len(existing) + 1
        sheet_recap.update_acell(f'B{next_row}', barcode_val)
        sheet_recap.update_acell(f'C{next_row}', ts)

        # Simpan ke Sheet Harian
        try:
            ws_daily = sh.worksheet(date_str)
        except gspread.WorksheetNotFound:
            ws_daily = sh.add_worksheet(title=date_str, rows="1000", cols="5")
            ws_daily.append_row(["Barcode", "Jam"])
        
        ws_daily.append_row([barcode_val, ts])
        return True, "Berhasil"
    except:
        return False, "Error System"

# --- INTERFACE UTAMA ---
if sh:
    st.markdown("<h1 class='main-title'>⚡SCANNER WAHANA</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📸 Live Camera Scan")
        # Kalender Persistent
        date_input = st.date_input("Tanggal Rekap", value=st.session_state['recap_date'])
        st.session_state['recap_date'] = date_input

        # VIDEO TRANSFORMER UNTUK AUTO-DETEKSI
        class BarcodeProcessor(VideoTransformerBase):
            def transform(self, frame):
                img = frame.to_ndarray(format="bgr24")
                barcodes = decode(img)
                for barcode in barcodes:
                    data = barcode.data.decode('utf-8')
                    # Gambar kotak di sekitar barcode untuk visual feedback
                    (x, y, w, h) = barcode.rect
                    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    
                    if data != st.session_state.get('last_detected'):
                        st.session_state['last_detected'] = data
                        # Trigger simpan data
                return img

        webrtc_streamer(
            key="scanner",
            video_transformer_factory=BarcodeProcessor,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": True, "audio": False},
        )

        # Logic Auto-Enter setelah deteksi
        if st.session_state['last_detected']:
            barcode_now = st.session_state['last_detected']
            success, msg = push_data(barcode_now)
            if success:
                st.toast(f"✅ TERDATA: {barcode_now}", icon="🚀")
                st.session_state['last_detected'] = None # Reset agar bisa scan barcode lain
                time.sleep(1)
                st.rerun()
            elif msg == "Duplikat":
                st.warning(f"⚠️ {barcode_now} sudah pernah di-scan.")
                st.session_state['last_detected'] = None

    with col2:
        st.subheader("📊 Recent Updates")
        try:
            sheet_recap = sh.worksheet("Report Recap")
            raw = sheet_recap.get_all_values()
            
            if len(raw) > 1:
                # Perbaikan Logika Tabel Error:
                # Ambil data, abaikan header, buat DF, lalu balik urutan
                df = pd.DataFrame(raw[1:], columns=["No", "Barcode", "Waktu"])
                df_reversed = df.iloc[::-1].reset_index(drop=True)
                
                # Tampilkan tabel statis (lebih stabil untuk auto-refresh)
                st.dataframe(df_reversed.head(15), use_container_width=True, hide_index=True)
                
                if st.button("🗑️ Reset Terakhir (Hapus Baris Terbawah GSheet)"):
                    sheet_recap.delete_rows(len(raw))
                    st.toast("Baris terakhir dihapus!")
                    st.rerun()
            else:
                st.info("Kosong")
        except Exception as e:
            st.error(f"Table Error: {e}")

st.caption("Cinnamoroll Wahana System v4.0 - Real-time WebRTC")
