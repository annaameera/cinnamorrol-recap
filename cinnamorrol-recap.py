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
st.set_page_config(page_title="Wahana Recap v5.2", page_icon="☁️", layout="wide")

# --- SESSION STATE ---
if 'recap_date' not in st.session_state:
    st.session_state['recap_date'] = datetime.now()
if 'last_code' not in st.session_state:
    st.session_state['last_code'] = ""

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0ea5e9 0%, #e0f2fe 100%); }
    div[data-testid="stForm"], .glossy-card {
        background: rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(15px);
        border-radius: 20px;
        padding: 20px;
    }
    .main-title { color: #000; font-weight: 900; text-align: center; font-size: 2.5rem; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- KONEKSI GSHEET (Pointed to Report Recap GID) ---
def init_gsheet_connection():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        # Buka spreadsheet berdasarkan URL spesifik
        url = "https://docs.google.com/spreadsheets/d/1vlwLdTxPLDnDkrn4luNKnRr_SH5TG-YJXK5NZAdWCVQ/edit#gid=925436264"
        spreadsheet = client.open_by_url(url)
        return spreadsheet.worksheet("Report Recap")
    except Exception as e:
        st.error(f"Koneksi Gagal: {e}")
        return None

# Ambil objek worksheet master
sheet_master = init_gsheet_connection()

# --- FUNGSI SIMPAN DATA ---
def save_data(barcode_val, date_obj):
    if not barcode_val: return False
    try:
        ts = datetime.now().strftime("%H:%M:%S")
        sheet_daily_name = date_obj.strftime("%d_%m_%Y_Rekap Wahana")
        
        # Cek duplikat di kolom B (Barcode)
        all_b = sheet_master.col_values(2)
        if barcode_val in all_b:
            st.toast(f"⚠️ DUPLIKAT: {barcode_val}", icon="⚠️")
            return False

        # 1. Update Master Report Recap (Kolom B & C)
        # Kolom A biasanya Auto-Number/Manual, kita update B dan C
        next_row = len(all_b) + 1
        sheet_master.update_acell(f'B{next_row}', barcode_val)
        sheet_master.update_acell(f'C{next_row}', ts)
        
        # 2. Update Sheet Harian (Dynamic)
        try:
            sh = sheet_master.spreadsheet
            ws_daily = sh.worksheet(sheet_daily_name)
        except gspread.WorksheetNotFound:
            ws_daily = sh.add_worksheet(title=sheet_daily_name, rows="1000", cols="5")
            ws_daily.append_row(["Barcode", "Timestamp"])
        ws_daily.append_row([barcode_val, ts])
        
        return True
    except Exception as e:
        st.error(f"Error Simpan: {e}")
        return False

# --- UI DASHBOARD ---
if sheet_master:
    st.markdown("<h1 class='main-title'>☁️ WAHANA RECAP v5.2</h1>", unsafe_allow_html=True)
    
    col_input, col_table = st.columns([1, 1.2])

    with col_input:
        st.markdown("### 📥 Panel Scan")
        date_pick = st.date_input("📅 TANGGAL REKAP", value=st.session_state['recap_date'])
        st.session_state['recap_date'] = date_pick
        
        # --- AUTO SCANNER ---
        def video_callback(frame):
            img = frame.to_ndarray(format="bgr24")
            for obj in decode(img):
                st.session_state['detected_now'] = obj.data.decode('utf-8')
            return frame.from_ndarray(img, format="bgr24")

        webrtc_streamer(
            key="wahana-scan-v5",
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

        # --- MANUAL INPUT ---
        with st.form("manual_entry", clear_on_submit=True):
            st.write("⌨️ **Input Manual / Honeywell**")
            manual_val = st.text_input("Barcode Value")
            if st.form_submit_button("SIMPAN ✨") and manual_val:
                if save_data(manual_val, date_pick):
                    st.toast("✅ Berhasil!")
                    time.sleep(1)
                    st.rerun()

    with col_table:
        st.markdown("### 📊 Live Table (Report Recap A:C)")
        try:
            # Tarik data Kolom A, B, C saja
            # get_all_values mengambil semua, kita filter di Python agar ringan
            raw_data = sheet_master.get_all_values()
            
            if len(raw_data) > 0:
                header = ["No", "Data Barcode", "Timestamp"]
                # Saring hanya baris yang punya data dan ambil kolom 0, 1, 2
                data_list = [r[:3] for r in raw_data[1:] if any(r)]
                
                if data_list:
                    df = pd.DataFrame(data_list, columns=header)
                    # Balik: Terbaru di baris 0
                    df_view = df.iloc[::-1].reset_index(drop=True)
                    df_view.insert(0, "Pilih", False)

                    edited_df = st.data_editor(
                        df_view.head(15), 
                        column_config={"Pilih": st.column_config.CheckboxColumn(required=True)},
                        disabled=header,
                        hide_index=True,
                        use_container_width=True,
                        key="master_editor"
                    )

                    if st.button("🗑️ HAPUS DATA TERPILIH"):
                        selected_indices = edited_df[edited_df["Pilih"] == True].index.tolist()
                        if selected_indices:
                            # Kalkulasi baris asli: Total_Baris - index_tampilan
                            total_rows = len(raw_data)
                            # Hapus dari indeks terbesar ke terkecil agar urutan gspread tidak rusak di tengah proses
                            for idx in sorted(selected_indices, reverse=False):
                                real_row_idx = total_rows - idx
                                sheet_master.delete_rows(int(real_row_idx))
                            
                            st.toast("🗑️ Data Terhapus!")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.info("Belum ada data terekam di sheet.")
            else:
                st.warning("Sheet Report Recap tidak memiliki data.")
        except Exception as e:
            st.error(f"Gagal memuat tabel: {e}")

st.caption("Cinnamoroll Wahana System v5.2 - Locked Column A,B,C")
