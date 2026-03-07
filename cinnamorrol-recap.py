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

# --- INISIALISASI SESSION STATE ---
if 'temp_data' not in st.session_state:
    st.session_state['temp_data'] = []
if 'input_key' not in st.session_state:
    st.session_state['input_key'] = 0
if 'selected_user' not in st.session_state:
    st.session_state['selected_user'] = None

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

# --- FUNGSI AMBIL DATA KARYAWAN (KOLOM D & E) ---
def get_employee_list():
    try:
        ss = client.open_by_url(spreadsheet_url)
        ws = ss.worksheet("Report Recap")
        # Ambil kolom D (NIP) dan E (Nama)
        nips = ws.col_values(4)[1:] # Mulai baris 2
        names = ws.col_values(5)[1:] # Mulai baris 2
        
        # Gabungkan menjadi format "Nama - NIP"
        employees = []
        for nip, name in zip(nips, names):
            if nip.strip() and name.strip():
                employees.append(f"{name.strip()} - {nip.strip()}")
        return sorted(list(set(employees))) # Unik & urut abjad
    except:
        return ["Admin - 000"]

# --- FUNGSI PROSES INPUT ---
def process_rapid_input():
    key = f"barcode_in_{st.session_state['input_key']}"
    val = st.session_state.get(key, "").strip().upper()
    if val:
        buffer_codes = [d['barcode'] for d in st.session_state['temp_data']]
        if val not in buffer_codes:
            ts = datetime.now(tz_indo).strftime("%H:%M:%S")
            st.session_state['temp_data'].append({
                'barcode': val, 
                'time': ts,
                'petugas': st.session_state['selected_user']
            })
            st.toast(f"📥 Antrean: {val}")
        st.session_state['input_key'] += 1

# --- FUNGSI SINKRONISASI (MULTI-DEVICE & IDENTITY) ---
def sync_with_identity():
    if not st.session_state['temp_data']:
        st.warning("Antrean kosong!")
        return
    if not st.session_state['selected_user']:
        st.error("Pilih nama karyawan dulu!")
        return

    target_date = datetime.now(tz_indo).date().strftime("%d_%m_%Y_Rekap Wahana")

    with st.spinner("Mengunggah data dengan identitas petugas..."):
        try:
            ss = client.open_by_url(spreadsheet_url)
            try:
                ws = ss.worksheet(target_date)
            except gspread.WorksheetNotFound:
                ws = ss.add_worksheet(title=target_date, rows="1000", cols="6")
                ws.append_row(["No", "Barcode", "Timestamp", "Petugas (Nama-NIP)"])

            existing_b = ws.col_values(2)
            existing_clean = [str(b).strip().upper() for b in existing_b]

            rows_to_push = []
            for item in st.session_state['temp_data']:
                if item['barcode'] not in existing_clean:
                    # Susun data: No (Rumus), Barcode, Jam, Nama-NIP
                    rows_to_push.append(["=ROW()-1", item['barcode'], item['time'], item['petugas']])
            
            if rows_to_push:
                ws.append_rows(rows_to_push, value_input_option='USER_ENTERED')
                st.session_state['temp_data'] = []
                st.success(f"✅ Sinkron {len(rows_to_push)} data berhasil!")
                time.sleep(1)
                st.rerun()
            else:
                st.session_state['temp_data'] = []
                st.info("Data sudah ada di Cloud.")
        except Exception as e:
            st.error(f"Error: {e}")

# --- UI DASHBOARD ---
st.markdown("<h2 style='text-align: center;'>💼 WAHANA RECAP</h2>", unsafe_allow_html=True)

# Sidebar untuk Identitas (Agar tidak berubah-ubah secara tidak sengaja)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1535/1535024.png", width=100)
    st.header("Profil Petugas")
    employee_options = get_employee_list()
    st.session_state['selected_user'] = st.selectbox("Pilih Nama / NIP Anda:", employee_options)
    st.info(f"Petugas Aktif: \n{st.session_state['selected_user']}")

col_l, col_r = st.columns([1, 1.2])

with col_l:
    st.markdown("### 🏹 SandBox Scan")
    st.text_input("SCAN DI SINI", key=f"barcode_in_{st.session_state['input_key']}", on_change=process_rapid_input)
    
    if st.button("🚀 SINKRON KE CLOUD", use_container_width=True, type="primary"):
        sync_with_identity()

    if st.session_state['temp_data']:
        st.divider()
        st.write("**Preview Antrean Lokal:**")
        st.dataframe(pd.DataFrame(st.session_state['temp_data']).iloc[::-1], use_container_width=True)

with col_r:
    st.markdown("### 📸 Kamera")
    def video_callback(frame):
        img = frame.to_ndarray(format="bgr24")
        for obj in decode(img):
            code = obj.data.decode('utf-8').strip().upper()
            if not any(d['barcode'] == code for d in st.session_state['temp_data']):
                ts = datetime.now(tz_indo).strftime("%H:%M:%S")
                st.session_state['temp_data'].append({
                    'barcode': code, 
                    'time': ts,
                    'petugas': st.session_state['selected_user']
                })
        return frame.from_ndarray(img, format="bgr24")

    webrtc_streamer(key="cam_ent", video_frame_callback=video_callback, media_stream_constraints={"video": True, "audio": False})

st.caption(f"v6.4 | Terhubung ke: {spreadsheet_url.split('/')[-2][:10]}... | User: {st.session_state['selected_user']}")
