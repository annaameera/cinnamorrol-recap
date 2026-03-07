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

# --- INISIALISASI BUFFER ---
if 'temp_data' not in st.session_state:
    st.session_state['temp_data'] = [] # Antrean lokal (RAM)
if 'input_key' not in st.session_state:
    st.session_state['input_key'] = 0 # Untuk meriset widget input secara paksa

# --- CSS GLOSSY ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); }
    .status-box { padding: 10px; border-radius: 10px; background: white; border: 1px solid #ddd; }
    input { font-size: 1.5rem !important; font-weight: bold; color: #1e40af !important; }
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

# --- FUNGSI PROSES INPUT (INSTAN) ---
def process_input():
    # Ambil nilai dari session state berdasarkan key dinamis
    val = st.session_state.get(f"barcode_in_{st.session_state['input_key']}", "").strip().upper()
    
    if val:
        # Cek duplikat di antrean lokal agar tidak dobel input dalam satu sesi
        buffer_codes = [d['barcode'] for d in st.session_state['temp_data']]
        
        if val not in buffer_codes:
            ts = datetime.now(tz_indo).strftime("%H:%M:%S")
            # "Cut & Paste" ke antrean lokal
            st.session_state['temp_data'].append({'barcode': val, 'time': ts})
            st.toast(f"✅ Terpindah ke Antrean: {val}")
        else:
            st.toast(f"⚠️ {val} sudah ada di antrean!", icon="⚠️")
        
        # Increment key untuk "membuang" widget lama dan membuat widget input baru yang kosong
        st.session_state['input_key'] += 1

# --- FUNGSI SINKRONISASI MASSAL ---
def sync_all():
    if not st.session_state['temp_data']:
        st.warning("Antrean kosong!")
        return

    with st.spinner("Mengunggah data ke Cloud..."):
        try:
            # Ambil data GSheet untuk cek duplikat final
            all_b = sheet_master.col_values(2)
            clean_existing = [str(b).strip().upper() for b in all_b]
            
            rows_to_push = []
            for item in st.session_state['temp_data']:
                if item['barcode'] not in clean_existing:
                    # Format: No, Barcode, Jam
                    rows_to_push.append([len(clean_existing) + len(rows_to_push) + 1, item['barcode'], item['time']])
            
            if rows_to_push:
                # Batch update (Sangat cepat untuk banyak data)
                start_row = len(clean_existing) + 1
                end_row = start_row + len(rows_to_push) - 1
                sheet_master.update(f"A{start_row}:C{end_row}", rows_to_push)
                
                st.session_state['temp_data'] = [] # Kosongkan antrean
                st.success(f"🔥 Berhasil sinkron {len(rows_to_push)} data!")
                time.sleep(1)
                st.rerun()
            else:
                st.session_state['temp_data'] = []
                st.info("Semua data di antrean ternyata sudah ada di GSheet.")
        except Exception as e:
            st.error(f"Gagal sinkron: {e}")

# --- UI DASHBOARD ---
st.markdown("<h2 style='text-align: center;'>⚡ WAHANA RECAP</h2>", unsafe_allow_html=True)

col_l, col_r = st.columns([1, 1.2])

with col_l:
    st.markdown("### 🏹 Laser Focus Input")
    st.info("Honeywell Auto-Enter akan langsung memindahkan data ke tabel antrean.")
    
    # Widget Input dengan Key Dinamis (Trik untuk auto-clear)
    st.text_input(
        "SCAN DI SINI", 
        key=f"barcode_in_{st.session_state['input_key']}", 
        on_change=process_input,
        placeholder="Ready to scan..."
    )
    
    st.write("")
    if st.button("🚀 SINKRONKAN SEMUA KE CLOUD", use_container_width=True, type="primary"):
        sync_all()
    
    st.divider()
    st.markdown("### 📸 Camera Scan")
    def video_callback(frame):
        img = frame.to_ndarray(format="bgr24")
        for obj in decode(img):
            code = obj.data.decode('utf-8').strip().upper()
            # Logika auto-input dari kamera
            buffer_codes = [d['barcode'] for d in st.session_state['temp_data']]
            if code not in buffer_codes:
                ts = datetime.now(tz_indo).strftime("%H:%M:%S")
                st.session_state['temp_data'].append({'barcode': code, 'time': ts})
        return frame.from_ndarray(img, format="bgr24")

    webrtc_streamer(key="cam", video_frame_callback=video_callback, 
                    media_stream_constraints={"video": True, "audio": False})

with col_r:
    st.markdown(f"### 📊 Antrean Lokal ({len(st.session_state['temp_data'])})")
    if st.session_state['temp_data']:
        # Tampilkan data terbaru di atas agar user tahu input berhasil
        df_view = pd.DataFrame(st.session_state['temp_data']).iloc[::-1]
        st.dataframe(df_view, use_container_width=True, height=400)
        
        if st.button("🗑️ Kosongkan Antrean"):
            st.session_state['temp_data'] = []
            st.rerun()
    else:
        st.success("✨ Antrean Bersih. Siap menembak data!")

st.caption("V6.1")
