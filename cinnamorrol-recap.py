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

# --- FUNGSI AMBIL DATA KARYAWAN ---
def get_employee_list():
    try:
        ss = client.open_by_url(spreadsheet_url)
        ws = ss.worksheet("Report Recap")
        nips = ws.col_values(4)[1:] 
        names = ws.col_values(5)[1:] 
        employees = [f"{n.strip()} - {p.strip()}" for p, n in zip(nips, names) if p.strip() and n.strip()]
        return sorted(list(set(employees)))
    except:
        return ["Petugas Umum - 000"]

# --- FUNGSI PROSES INPUT ---
def process_rapid_input():
    key = f"barcode_in_{st.session_state['input_key']}"
    val = st.session_state.get(key, "").strip().upper()
    if val:
        buffer_codes = [d['barcode'] for d in st.session_state['temp_data']]
        if val not in buffer_codes:
            ts = datetime.now(tz_indo).strftime("%H:%M:%S")
            st.session_state['temp_data'].append({
                'Pilih': False,
                'barcode': val, 
                'time': ts,
                'petugas': st.session_state.get('selected_user', 'Unknown')
            })
            st.toast(f"📥 Masuk Antrean: {val}")
        else:
            st.toast(f"⚠️ {val} sudah ada di antrean!", icon="⚠️")
        st.session_state['input_key'] += 1

# --- UI DASHBOARD ---
st.markdown("<h2 style='text-align: center;'>💼 WAHANA RECAP</h2>", unsafe_allow_html=True)

with st.sidebar:
    st.header("Profil Petugas")
    emp_list = get_employee_list()
    st.session_state['selected_user'] = st.selectbox("Identitas Anda:", emp_list)
    st.divider()
    st.info("Gunakan tabel di kanan untuk menghapus data yang salah sebelum sinkron.")

col_l, col_r = st.columns([1, 1.4])

with col_l:
    st.markdown("### 🏹 SandBox Scan")
    st.text_input("SCAN DI SINI", key=f"barcode_in_{st.session_state['input_key']}", on_change=process_rapid_input)
    
    if st.button("🚀 UPLOAD KE CLOUD", use_container_width=True, type="primary"):
        if not st.session_state['temp_data']:
            st.warning("Antrean kosong!")
        else:
            target_date = datetime.now(tz_indo).date().strftime("%d_%m_%Y_Rekap Wahana")
            try:
                ss = client.open_by_url(spreadsheet_url)
                try:
                    ws = ss.worksheet(target_date)
                except gspread.WorksheetNotFound:
                    ws = ss.add_worksheet(title=target_date, rows="1000", cols="6")
                    ws.append_row(["No", "Barcode", "Timestamp", "Petugas"])

                existing_b = [str(b).strip().upper() for b in ws.col_values(2)]
                rows_to_push = [["=ROW()-1", i['barcode'], i['time'], i['petugas']] 
                                for i in st.session_state['temp_data'] if i['barcode'] not in existing_b]
                
                if rows_to_push:
                    ws.append_rows(rows_to_push, value_input_option='USER_ENTERED')
                    st.session_state['temp_data'] = []
                    st.success(f"✅ Berhasil sinkron {len(rows_to_push)} data!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.session_state['temp_data'] = []
                    st.info("Data sudah ada di cloud.")
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()
    st.markdown("### 📸 Kamera")
    def video_callback(frame):
        img = frame.to_ndarray(format="bgr24")
        for obj in decode(img):
            code = obj.data.decode('utf-8').strip().upper()
            if not any(d['barcode'] == code for d in st.session_state['temp_data']):
                ts = datetime.now(tz_indo).strftime("%H:%M:%S")
                st.session_state['temp_data'].append({
                    'Pilih': False, 'barcode': code, 'time': ts, 
                    'petugas': st.session_state.get('selected_user')
                })
        return frame.from_ndarray(img, format="bgr24")

    webrtc_streamer(key="cam_v65", video_frame_callback=video_callback, 
                    media_stream_constraints={"video": True, "audio": False})

with col_r:
    st.markdown(f"### 📋 Kelola Antrean ({len(st.session_state['temp_data'])})")
    
    if st.session_state['temp_data']:
        # Konversi ke DataFrame untuk editing
        df_queue = pd.DataFrame(st.session_state['temp_data'])
        
        # Tampilkan editor tabel
        edited_df = st.data_editor(
            df_queue,
            column_config={
                "Pilih": st.column_config.CheckboxColumn("Hapus?", default=False),
                "barcode": st.column_config.TextColumn("Barcode", disabled=True),
                "time": st.column_config.TextColumn("Jam", disabled=True),
                "petugas": st.column_config.TextColumn("Petugas", disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            key="queue_editor"
        )

        col_del1, col_del2 = st.columns(2)
        with col_del1:
            if st.button("🗑️ HAPUS DATA TERPILIH", use_container_width=True):
                # Filter data: ambil yang checkbox 'Pilih' nya False (tidak dicentang)
                remaining_data = edited_df[edited_df['Pilih'] == False].to_dict('records')
                st.session_state['temp_data'] = remaining_data
                st.rerun()
        
        with col_del2:
            if st.button("❌ BERSIHKAN SEMUA", use_container_width=True):
                st.session_state['temp_data'] = []
                st.rerun()
    else:
        st.info("Belum ada data di antrean. Silakan scan.")

st.caption("v6.5")
