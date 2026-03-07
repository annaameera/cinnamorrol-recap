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
    st.session_state['temp_data'] = []
if 'input_key' not in st.session_state:
    st.session_state['input_key'] = 0
if 'selected_date' not in st.session_state:
    st.session_state['selected_date'] = datetime.now(tz_indo).date()

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 100%); }
    .main-card { background: white; padding: 20px; border-radius: 15px; border: 1px solid #bae6fd; }
    input { font-size: 1.4rem !important; font-weight: bold; color: #0369a1 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- KONEKSI GSHEET ---
@st.cache_resource
def init_gsheet_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        return gspread.authorize(creds)
    except: return None

client = init_gsheet_client()
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1vlwLdTxPLDnDkrn4luNKnRr_SH5TG-YJXK5NZAdWCVQ/edit"

# --- FUNGSI PROSES INPUT (RAPID-FIRE) ---
def process_rapid_input():
    key = f"barcode_in_{st.session_state['input_key']}"
    val = st.session_state.get(key, "").strip().upper()
    
    if val:
        buffer_codes = [d['barcode'] for d in st.session_state['temp_data']]
        if val not in buffer_codes:
            ts = datetime.now(tz_indo).strftime("%H:%M:%S")
            st.session_state['temp_data'].append({'barcode': val, 'time': ts})
            st.toast(f"📥 Masuk Antrean: {val}")
        else:
            st.toast(f"⚠️ {val} sudah ada di antrean lokal!", icon="⚠️")
        
        st.session_state['input_key'] += 1

# --- FUNGSI SINKRONISASI KE SHEET TANGGAL (CALENDAR TARGET) ---
def sync_to_calendar_sheet():
    if not st.session_state['temp_data']:
        st.warning("Antrean masih kosong, tembak barcode dulu!")
        return

    # Nama Sheet Berdasarkan Kalender: DD_MM_YYYY_Rekap Wahana
    sheet_name = st.session_state['selected_date'].strftime("%d_%m_%Y_Rekap Wahana")

    with st.spinner(f"Menyinkronkan ke sheet: {sheet_name}..."):
        try:
            ss = client.open_by_url(spreadsheet_url)
            
            # Cek apakah sheet sudah ada, jika belum buat baru
            try:
                ws = ss.worksheet(sheet_name)
            except gspread.WorksheetNotFound:
                ws = ss.add_worksheet(title=sheet_name, rows="1000", cols="5")
                ws.append_row(["No", "Barcode", "Timestamp"]) # Header
            
            # Ambil data yang sudah ada di sheet tersebut untuk cek duplikat & nomor urut
            existing_data = ws.get_all_values()
            existing_barcodes = [str(r[1]).strip().upper() for r in existing_data[1:]] if len(existing_data) > 1 else []
            
            rows_to_push = []
            for item in st.session_state['temp_data']:
                if item['barcode'] not in existing_barcodes:
                    no_urut = len(existing_data) + len(rows_to_push)
                    rows_to_push.append([no_urut, item['barcode'], item['time']])
            
            if rows_to_push:
                ws.append_rows(rows_to_push)
                st.session_state['temp_data'] = [] # Reset antrean lokal
                st.success(f"🔥 Berhasil kirim {len(rows_to_push)} data ke '{sheet_name}'!")
                time.sleep(1)
                st.rerun()
            else:
                st.session_state['temp_data'] = []
                st.info(f"Semua data di antrean sudah ada di sheet '{sheet_name}'.")
                
        except Exception as e:
            st.error(f"Gagal sinkronisasi: {e}")

# --- UI DASHBOARD ---
st.markdown("<h2 style='text-align: center;'>⚡ WAHANA RECAP</h2>", unsafe_allow_html=True)

col_l, col_r = st.columns([1, 1.2])

with col_l:
    st.markdown("### 📅 Konfigurasi & Input")
    
    # Pilih Tanggal (Menentukan Nama Sheet Tujuan)
    selected_date = st.date_input("PILIH TANGGAL REKAP", value=st.session_state['selected_date'])
    st.session_state['selected_date'] = selected_date
    
    st.markdown("---")
    
    # Input Honeywell (Rapid Fire)
    st.text_input(
        "SCAN BARCODE (AUTO-ENTER)", 
        key=f"barcode_in_{st.session_state['input_key']}", 
        on_change=process_rapid_input,
        placeholder="Tembak laser di sini..."
    )
    
    st.write("")
    if st.button("🚀 SINKRONKAN KE CLOUD", use_container_width=True, type="primary"):
        sync_to_calendar_sheet()
    
    st.divider()
    st.markdown("### 📸 Kamera Scan")
    def video_callback(frame):
        img = frame.to_ndarray(format="bgr24")
        for obj in decode(img):
            code = obj.data.decode('utf-8').strip().upper()
            buffer_codes = [d['barcode'] for d in st.session_state['temp_data']]
            if code not in buffer_codes:
                ts = datetime.now(tz_indo).strftime("%H:%M:%S")
                st.session_state['temp_data'].append({'barcode': code, 'time': ts})
        return frame.from_ndarray(img, format="bgr24")

    webrtc_streamer(key="cam_sync", video_frame_callback=video_callback, 
                    media_stream_constraints={"video": True, "audio": False})

with col_r:
    st.markdown(f"### 📋 Antrean Lokal (Target: {st.session_state['selected_date'].strftime('%d/%m/%Y')})")
    
    if st.session_state['temp_data']:
        df_view = pd.DataFrame(st.session_state['temp_data']).iloc[::-1]
        st.dataframe(df_view, use_container_width=True, height=450)
        
        if st.button("🗑️ Reset Antrean"):
            st.session_state['temp_data'] = []
            st.rerun()
    else:
        st.success("✨ Antrean kosong. Siap mulai rekap!")

st.caption("v6.2")
