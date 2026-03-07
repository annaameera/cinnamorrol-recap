import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import time
import pytz
from streamlit_webrtc import webrtc_streamer
import cv2
import numpy as np
from pyzbar.pyzbar import decode

# --- KONFIGURASI ---
st.set_page_config(page_title="Wahana Recap", layout="wide")
tz_indo = pytz.timezone('Asia/Jakarta')

# --- INISIALISASI BUFFER (KUNCI KECEPATAN) ---
if 'temp_data' not in st.session_state:
    st.session_state['temp_data'] = [] # Data yang baru masuk tapi belum sinkron ke Cloud
if 'last_processed' not in st.session_state:
    st.session_state['last_processed'] = ""

# --- CSS GLOSSY ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f0f9ff 0%, #c7d2fe 100%); }
    .input-box { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .status-sync { color: #4338ca; font-weight: bold; font-size: 0.9rem; }
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
        url = "https://docs.google.com/spreadsheets/d/1vlwLdTxPLDnDkrn4luNKnRr_SH5TG-YJXK5NZAdWCVQ/edit"
        return client.open_by_url(url).worksheet("Report Recap")
    except: return None

sheet_master = init_gsheet()

# --- FUNGSI TURBO SAVE (MENGHINDARI LOADING LAMA) ---
def turbo_input(barcode_val):
    code = str(barcode_val).strip().upper()
    if not code or code == st.session_state['last_processed']:
        return
    
    # Cek Duplikat di Buffer Lokal (Super Cepat)
    buffer_codes = [d['barcode'] for d in st.session_state['temp_data']]
    if code in buffer_codes:
        st.toast(f"⚠️ Kode {code} sudah ada di antrean!", icon="⚠️")
        return

    # Simpan ke memori sementara (Instan)
    ts = datetime.now(tz_indo).strftime("%H:%M:%S")
    st.session_state['temp_data'].append({'barcode': code, 'time': ts})
    st.session_state['last_processed'] = code
    st.toast(f"📥 Masuk Antrean: {code}")

# --- PROSES SINKRONISASI KE CLOUD ---
def sync_to_cloud():
    if st.session_state['temp_data'] and sheet_master:
        with st.spinner("Menyinkronkan ke Cloud..."):
            try:
                # Ambil data Cloud untuk cek duplikat terakhir
                existing = sheet_master.col_values(2)
                
                rows_to_add = []
                for item in st.session_state['temp_data']:
                    if item['barcode'] not in existing:
                        rows_to_add.append([len(existing) + len(rows_to_add) + 1, item['barcode'], item['time']])
                
                if rows_to_add:
                    # Kirim semua data sekaligus (Batch Update) - JAUH LEBIH CEPAT
                    start_row = len(existing) + 1
                    end_row = start_row + len(rows_to_add) - 1
                    range_name = f"A{start_row}:C{end_row}"
                    sheet_master.update(range_name, rows_to_add)
                
                st.session_state['temp_data'] = [] # Kosongkan buffer setelah sukses
                st.success("✅ Sinkronisasi Berhasil!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"Gagal sinkron: {e}")

# --- UI DASHBOARD ---
st.markdown("<h2 style='text-align: center;'>☁️ WAHANA RECAP</h2>", unsafe_allow_html=True)

col_input, col_monitor = st.columns([1, 1.2])

with col_input:
    st.markdown("### ⚡ Fast Input")
    # Form input manual yang tidak reload seluruh halaman
    with st.container():
        manual_code = st.text_input("TEMBAK BARCODE DI SINI (AUTO-ENTER)", key="entry", placeholder="Scan sekarang...")
        if manual_code:
            turbo_input(manual_code)
            # Membersihkan input tanpa reload lamban
            st.empty() 

    if st.button("🚀 SINKRONKAN KE GSHEET", use_container_width=True):
        sync_to_cloud()
    
    st.divider()
    st.markdown("### 📸 Camera Scan")
    def video_callback(frame):
        img = frame.to_ndarray(format="bgr24")
        for obj in decode(img):
            turbo_input(obj.data.decode('utf-8'))
        return frame.from_ndarray(img, format="bgr24")

    webrtc_streamer(key="cam", video_frame_callback=video_callback, 
                    media_stream_constraints={"video": True, "audio": False})

with col_monitor:
    st.markdown(f"### 📊 Antrean Sementara ({len(st.session_state['temp_data'])})")
    if st.session_state['temp_data']:
        df_temp = pd.DataFrame(st.session_state['temp_data'])
        st.table(df_temp.iloc[::-1]) # Tampilkan antrean terbaru di atas
        if st.button("🗑️ Bersihkan Antrean"):
            st.session_state['temp_data'] = []
            st.rerun()
    else:
        st.info("Semua data sudah sinkron atau belum ada input.")

    st.markdown("---")
    st.markdown("### ☁️ Data di GSheet (Terakhir)")
    try:
        raw = sheet_master.get_all_values()
        if len(raw) > 1:
            df_cloud = pd.DataFrame([r[:3] for r in raw[1:]], columns=["No", "Barcode", "Jam"])
            st.dataframe(df_cloud.tail(10), use_container_width=True)
    except: pass

st.caption("V6.0")
