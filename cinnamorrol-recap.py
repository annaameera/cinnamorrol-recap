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
import pytz

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Wahana x IDX Recap", page_icon="🛡️", layout="wide")

# Zona Waktu Indonesia (WIB)
tz_indo = pytz.timezone('Asia/Jakarta')

# --- INISIALISASI SESSION STATE ---
if 'recap_date' not in st.session_state:
    st.session_state['recap_date'] = datetime.now(tz_indo)
if 'last_processed_code' not in st.session_state:
    st.session_state['last_processed_code'] = "" # Lapis 1: Cegah scan berulang di sesi aktif

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0ea5e9 0%, #e0f2fe 100%); }
    .main-title { color: #000; font-weight: 900; text-align: center; font-size: 2.5rem; text-transform: uppercase; }
    div[data-testid="stForm"] { background: rgba(255, 255, 255, 0.3); border-radius: 20px; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- KONEKSI GSHEET ---
def init_gsheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        url = "https://docs.google.com/spreadsheets/d/1vlwLdTxPLDnDkrn4luNKnRr_SH5TG-YJXK5NZAdWCVQ/edit"
        spreadsheet = client.open_by_url(url)
        return spreadsheet.worksheet("Report Recap")
    except Exception as e:
        st.error(f"Koneksi Gagal: {e}")
        return None

sheet_master = init_gsheet()

# --- FUNGSI SIMPAN DATA (ANTI-DUPLIKAT) ---
def save_data(barcode_val, date_obj):
    if not barcode_val: return False
    
    # Bersihkan spasi atau karakter aneh
    barcode_val = str(barcode_val).strip()
    
    try:
        # Lapis 2: Cek di GSheet (Kolom B)
        all_barcodes = sheet_master.col_values(2) # Ambil semua data di kolom B
        if barcode_val in all_barcodes:
            st.toast(f"⚠️ GAGAL! Kode {barcode_val} sudah ada di GSheet.", icon="🚫")
            st.warning(f"Barcode `{barcode_val}` terdeteksi duplikat!")
            return False
            
        # Jika lolos cek duplikat, buat timestamp WIB 24 Jam
        ts = datetime.now(tz_indo).strftime("%H:%M:%S")
        sheet_daily_name = date_obj.strftime("%d_%m_%Y_Rekap Wahana")
        
        # Hitung baris berikutnya
        next_row = len(all_barcodes) + 1
        
        # Simpan ke Master (Kolom B & C)
        sheet_master.update_acell(f'B{next_row}', barcode_val)
        sheet_master.update_acell(f'C{next_row}', ts)
        
        # Simpan ke Sheet Harian
        try:
            sh = sheet_master.spreadsheet
            ws_daily = sh.worksheet(sheet_daily_name)
        except gspread.WorksheetNotFound:
            ws_daily = sh.add_worksheet(title=sheet_daily_name, rows="1000", cols="5")
            ws_daily.append_row(["Barcode", "Timestamp"])
        ws_daily.append_row([barcode_val, ts])
        
        return True
    except Exception as e:
        st.error(f"Error Database: {e}")
        return False

# --- UI DASHBOARD ---
if sheet_master:
    st.markdown("<h1 class='main-title'>🛡️ WAHANA RECAP</h1>", unsafe_allow_html=True)
    
    col_l, col_r = st.columns([1, 1.2])

    with col_l:
        st.markdown("### 📥 Scanner Panel")
        date_pick = st.date_input("📅 TANGGAL", value=st.session_state['recap_date'])
        st.session_state['recap_date'] = date_pick
        
        # 📸 Kamera Auto-Scan
        def video_callback(frame):
            img = frame.to_ndarray(format="bgr24")
            for obj in decode(img):
                code = obj.data.decode('utf-8')
                # Lapis 3: Cek session state sebelum trigger simpan
                if code != st.session_state['last_processed_code']:
                    st.session_state['detected_now'] = code
            return frame.from_ndarray(img, format="bgr24")

        webrtc_streamer(
            key="scanner_v57",
            video_frame_callback=video_callback,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": True, "audio": False}
        )

        # Proses hasil scan otomatis
        if 'detected_now' in st.session_state:
            scanned_code = st.session_state['detected_now']
            if save_data(scanned_code, date_pick):
                st.toast(f"✅ Berhasil: {scanned_code}")
                st.session_state['last_processed_code'] = scanned_code # Kunci kode agar tidak dobel scan
                del st.session_state['detected_now']
                time.sleep(1)
                st.rerun()
            else:
                # Jika gagal (duplikat), tetap kunci kodenya agar kamera tidak berteriak terus
                st.session_state['last_processed_code'] = scanned_code
                del st.session_state['detected_now']

        # ⌨️ Input Manual
        with st.form("manual_entry", clear_on_submit=True):
            m_barcode = st.text_input("Barcode / Resi (Manual)")
            if st.form_submit_button("SIMPAN DATA ✨") and m_barcode:
                if save_data(m_barcode, date_pick):
                    st.toast("✅ Data Manual Tersimpan!")
                    time.sleep(1)
                    st.rerun()

    with col_r:
        st.markdown("### 📊 Recent Updates")
        try:
            raw = sheet_master.get_all_values()
            if len(raw) > 1:
                data_rows = []
                for i, r in enumerate(raw[1:]):
                    # Ambil kolom A, B, C (index 0, 1, 2)
                    row_data = (r + ["", "", ""])[:3]
                    data_rows.append([i + 2] + row_data)

                df = pd.DataFrame(data_rows, columns=["Gsheet_Row", "No", "Recap", "Timestamp"])
                df.insert(0, "Pilih", False)

                edited = st.data_editor(
                    df,
                    column_config={"Gsheet_Row": None, "Pilih": st.column_config.CheckboxColumn(required=True)},
                    disabled=["No", "Recap", "Timestamp"],
                    hide_index=True,
                    use_container_width=True,
                    key="table_final"
                )

                if st.button("🗑️ CLEAR KOLOM A-C TERPILIH"):
                    to_clear = edited[edited["Pilih"] == True]["Gsheet_Row"].tolist()
                    if to_clear:
                        for row_num in to_clear:
                            # Hapus hanya range A-C tanpa geser baris
                            sheet_master.batch_clear([f'A{row_num}:C{row_num}'])
                        st.toast("🗑️ Data A-C dikosongkan!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("Tabel kosong.")
        except Exception as e:
            st.error(f"Error Table: {e}")

st.caption("v5.7")
