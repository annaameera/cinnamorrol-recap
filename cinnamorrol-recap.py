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

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Wahana Recap v5.5", page_icon="☁️", layout="wide")

if 'recap_date' not in st.session_state:
    st.session_state['recap_date'] = datetime.now()

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0ea5e9 0%, #e0f2fe 100%); }
    .main-title { color: #000; font-weight: 900; text-align: center; font-size: 2.5rem; text-transform: uppercase; }
    div[data-testid="stForm"] { background: rgba(255, 255, 255, 0.3); border-radius: 20px; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- KONEKSI GSHEET (Tanpa Cache) ---
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

# Panggil koneksi setiap kali skrip dijalankan (agar data fresh)
sheet_master = init_gsheet()

# --- FUNGSI SIMPAN DATA ---
def save_data(barcode_val, date_obj):
    if not barcode_val: return False
    try:
        ts = datetime.now().strftime("%H:%M:%S")
        sheet_daily_name = date_obj.strftime("%d_%m_%Y_Rekap Wahana")
        
        # Ambil kolom B untuk cek duplikat & hitung baris
        all_b = sheet_master.col_values(2)
        if barcode_val in all_b:
            st.toast(f"⚠️ DUPLIKAT: {barcode_val}", icon="⚠️")
            return False
            
        next_row = len(all_b) + 1
        
        # Update Master (Kolom B & C)
        sheet_master.update_acell(f'B{next_row}', barcode_val)
        sheet_master.update_acell(f'C{next_row}', ts)
        
        # Update Daily Sheet
        try:
            sh = sheet_master.spreadsheet
            ws_daily = sh.worksheet(sheet_daily_name)
        except gspread.WorksheetNotFound:
            ws_daily = sh.add_worksheet(title=sheet_daily_name, rows="1000", cols="5")
            ws_daily.append_row(["Barcode", "Timestamp"])
        ws_daily.append_row([barcode_val, ts])
        
        return True
    except Exception as e:
        st.error(f"Gagal simpan: {e}")
        return False

# --- UI DASHBOARD ---
if sheet_master:
    st.markdown("<h1 class='main-title'>☁️ WAHANA RECAP v5.5</h1>", unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1, 1.2])

    with col_left:
        st.markdown("### 📥 Input Panel")
        date_pick = st.date_input("📅 TANGGAL REKAP", value=st.session_state['recap_date'])
        st.session_state['recap_date'] = date_pick
        
        # 1. Camera Auto-Scan
        def video_callback(frame):
            img = frame.to_ndarray(format="bgr24")
            for obj in decode(img):
                st.session_state['detected_now'] = obj.data.decode('utf-8')
            return frame.from_ndarray(img, format="bgr24")

        webrtc_streamer(
            key="scanner",
            video_frame_callback=video_callback,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": True, "audio": False}
        )

        if 'detected_now' in st.session_state:
            if save_data(st.session_state['detected_now'], date_pick):
                st.toast("✅ Auto-Scan Berhasil!")
                del st.session_state['detected_now']
                time.sleep(1)
                st.rerun()

        # 2. Input Manual / Honeywell
        with st.form("manual_form", clear_on_submit=True):
            barcode_manual = st.text_input("Barcode Value (Manual/Honeywell)")
            if st.form_submit_button("SIMPAN DATA ✨") and barcode_manual:
                if save_data(barcode_manual, date_pick):
                    st.toast("✅ Tersimpan!")
                    time.sleep(1)
                    st.rerun()

    with col_right:
        st.markdown("### 📊 Mini Table (A, B, C)")
        try:
            # Mengambil data terbaru secara langsung tanpa filter cache
            raw_data = sheet_master.get_all_values()
            
            if len(raw_data) > 1:
                # Siapkan baris data dengan mapping baris asli GSheet
                header_names = ["No", "Barcode", "Timestamp"]
                rows = []
                for i, r in enumerate(raw_data[1:]):
                    # Simpan index baris asli (header=1, data mulai 2)
                    actual_row_num = i + 2
                    # Pastikan ambil kolom A, B, C (0, 1, 2)
                    clean_row = (r + ["", "", ""])[:3]
                    rows.append([actual_row_num] + clean_row)

                # Buat DataFrame (Tanpa sorting, data baru otomatis di bawah)
                df = pd.DataFrame(rows, columns=["Gsheet_Row", "No", "Barcode", "Timestamp"])
                df.insert(0, "Pilih", False)

                # Editor Tabel
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "Pilih": st.column_config.CheckboxColumn(required=True),
                        "Gsheet_Row": None, # Sembunyikan kolom index teknis
                        "No": st.column_config.TextColumn(width="small"),
                        "Barcode": st.column_config.TextColumn(width="medium"),
                        "Timestamp": st.column_config.TextColumn(width="small")
                    },
                    disabled=["No", "Barcode", "Timestamp"],
                    hide_index=True,
                    use_container_width=True,
                    key="table_v55"
                )

                # Logika Hapus
                if st.button("🗑️ HAPUS BARIS TERPILIH"):
                    to_delete = edited_df[edited_df["Pilih"] == True]["Gsheet_Row"].tolist()
                    if to_delete:
                        # Hapus dari baris terbesar ke terkecil agar index tidak bergeser
                        for row_num in sorted(to_delete, reverse=True):
                            sheet_master.delete_rows(int(row_num))
                        
                        st.toast(f"🗑️ {len(to_delete)} Data Terhapus!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("Tabel kosong. Silakan input data.")
        except Exception as e:
            st.error(f"Gagal memuat tabel: {e}")

st.caption("v5.5 - Data Terurut Sesuai Input (Terbaru di Bawah)")
