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
st.set_page_config(page_title="Wahana Recap", page_icon="🚫", layout="wide")
tz_indo = pytz.timezone('Asia/Jakarta')

if 'recap_date' not in st.session_state:
    st.session_state['recap_date'] = datetime.now(tz_indo)
if 'last_processed_code' not in st.session_state:
    st.session_state['last_processed_code'] = ""

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

# --- FUNGSI SIMPAN DATA (STRICT VALIDATION) ---
def save_data(barcode_val, date_obj):
    if not barcode_val: return False
    
    # STANDARISASI DATA: Hapus spasi & Ubah ke Huruf Besar
    clean_barcode = str(barcode_val).strip().upper()
    
    try:
        # TARIK DATA TERBARU DARI KOLOM B
        # Gunakan list comprehension untuk membersihkan data yang ditarik dari GSheet agar fair saat dicek
        existing_barcodes = [str(b).strip().upper() for b in sheet_master.col_values(2)]
        
        if clean_barcode in existing_barcodes:
            st.toast(f"🚫 DUPLIKAT TERDETEKSI: {clean_barcode}", icon="❌")
            st.warning(f"Data `{clean_barcode}` sudah ada di sistem. Gagal menyimpan.")
            return False
            
        # Jika lolos, simpan dengan format Indonesia 24 Jam
        ts = datetime.now(tz_indo).strftime("%H:%M:%S")
        sheet_daily_name = date_obj.strftime("%d_%m_%Y_Rekap Wahana")
        
        # Simpan ke Master (Kolom B & C)
        next_row = len(existing_barcodes) + 1
        sheet_master.update_acell(f'B{next_row}', clean_barcode)
        sheet_master.update_acell(f'C{next_row}', ts)
        
        # Simpan ke Sheet Harian
        try:
            sh = sheet_master.spreadsheet
            ws_daily = sh.worksheet(sheet_daily_name)
        except gspread.WorksheetNotFound:
            ws_daily = sh.add_worksheet(title=sheet_daily_name, rows="1000", cols="5")
            ws_daily.append_row(["Barcode", "Timestamp"])
        ws_daily.append_row([clean_barcode, ts])
        
        return True
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False

# --- UI DASHBOARD ---
if sheet_master:
    st.markdown("<h1 class='main-title'>WAHANA RECAP</h1>", unsafe_allow_html=True)
    
    col_l, col_r = st.columns([1, 1.2])

    with col_l:
        st.markdown("### 📥 Panel Scan")
        date_pick = st.date_input("📅 TANGGAL", value=st.session_state['recap_date'])
        st.session_state['recap_date'] = date_pick
        
        # SCANNER REAL-TIME
        def video_callback(frame):
            img = frame.to_ndarray(format="bgr24")
            for obj in decode(img):
                raw_code = obj.data.decode('utf-8')
                # Standarisasi saat deteksi kamera
                code = raw_code.strip().upper()
                if code != st.session_state['last_processed_code']:
                    st.session_state['detected_now'] = code
            return frame.from_ndarray(img, format="bgr24")

        webrtc_streamer(
            key="scanner_v58",
            video_frame_callback=video_callback,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": True, "audio": False}
        )

        if 'detected_now' in st.session_state:
            scanned = st.session_state['detected_now']
            if save_data(scanned, date_pick):
                st.toast(f"✅ Tersimpan: {scanned}")
                st.session_state['last_processed_code'] = scanned
                del st.session_state['detected_now']
                time.sleep(1)
                st.rerun()
            else:
                # Jika duplikat, tetap tandai agar kamera tidak scan ulang terus menerus
                st.session_state['last_processed_code'] = scanned
                del st.session_state['detected_now']

        with st.form("manual_entry", clear_on_submit=True):
            m_barcode = st.text_input("Barcode Manual (Sistem akan Auto-Uppercase)")
            if st.form_submit_button("SIMPAN DATA ✨") and m_barcode:
                if save_data(m_barcode, date_pick):
                    st.toast("✅ Berhasil!")
                    time.sleep(1)
                    st.rerun()

    with col_r:
        st.markdown("### 📊 Recent Updates")
        try:
            raw = sheet_master.get_all_values()
            if len(raw) > 1:
                data_rows = []
                for i, r in enumerate(raw[1:]):
                    # Ambil A, B, C
                    row_content = (r + ["", "", ""])[:3]
                    data_rows.append([i + 2] + row_content)

                df = pd.DataFrame(data_rows, columns=["Gsheet_Row", "No", "Barcode", "Timestamp"])
                df.insert(0, "Pilih", False)

                edited = st.data_editor(
                    df,
                    column_config={"Gsheet_Row": None, "Pilih": st.column_config.CheckboxColumn(required=True)},
                    disabled=["No", "Barcode", "Timestamp"],
                    hide_index=True,
                    use_container_width=True,
                    key="table_editor_v58"
                )

                if st.button("🗑️ BERSIHKAN KOLOM A-C"):
                    to_clear = edited[edited["Pilih"] == True]["Gsheet_Row"].tolist()
                    if to_clear:
                        for row_num in to_clear:
                            sheet_master.batch_clear([f'A{row_num}:C{row_num}'])
                        st.toast("🗑️ Kolom A-C Dikosongkan!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("Tabel kosong.")
        except Exception as e:
            st.error(f"Error Table: {e}")

st.caption("v5.8")
