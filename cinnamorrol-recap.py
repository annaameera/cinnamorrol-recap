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
st.set_page_config(page_title="Wahana Recap", page_icon="☁️", layout="wide")

# --- INISIALISASI SESSION STATE ---
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
        border: 1px solid rgba(255, 255, 255, 0.5);
        padding: 20px;
    }
    .main-title { color: #000; font-weight: 900; text-align: center; font-size: 2.5rem; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- KONEKSI GSHEET (Tanpa Cache untuk Tabel agar Real-time) ---
def get_gsheet_client():
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

sh = get_gsheet_client()

# --- FUNGSI SIMPAN DATA ---
def save_data(barcode_val, date_obj):
    if not barcode_val: return False
    try:
        sheet_recap = sh.worksheet("Report Recap")
        ts = datetime.now().strftime("%H:%M:%S")
        sheet_daily_name = date_obj.strftime("%d_%m_%Y_Rekap Wahana")
        
        # Cek duplikat di kolom B
        all_b = sheet_recap.col_values(2)
        if barcode_val in all_b:
            st.toast(f"⚠️ DUPLIKAT: {barcode_val}", icon="⚠️")
            return False

        # Update Master
        next_row = len(all_b) + 1
        sheet_recap.update_acell(f'B{next_row}', barcode_val)
        sheet_recap.update_acell(f'C{next_row}', ts)
        
        # Update Daily
        try:
            ws_daily = sh.worksheet(sheet_daily_name)
        except gspread.WorksheetNotFound:
            ws_daily = sh.add_worksheet(title=sheet_daily_name, rows="1000", cols="5")
            ws_daily.append_row(["Barcode", "Timestamp"])
        ws_daily.append_row([barcode_val, ts])
        
        return True
    except Exception as e:
        st.error(f"Gagal Simpan: {e}")
        return False

# --- UI UTAMA ---
if sh:
    st.markdown("<h1 class='main-title'>☁️ WAHANA RECAP</h1>", unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1, 1.2])

    with col_left:
        st.markdown("### 📥 Input Panel")
        
        # Kalender (Persistent)
        date_pick = st.date_input("📅 TANGGAL REKAP", value=st.session_state['recap_date'])
        st.session_state['recap_date'] = date_pick
        
        # 1. Camera Auto-Scan
        st.write("📸 **Auto-Scan Camera**")
        def video_callback(frame):
            img = frame.to_ndarray(format="bgr24")
            decoded = decode(img)
            for obj in decoded:
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
                st.toast(f"✅ Auto-Scan Berhasil!")
                del st.session_state['detected_now']
                time.sleep(1)
                st.rerun()

        # 2. Input Manual
        with st.form("manual_form", clear_on_submit=True):
            st.write("⌨️ **Input Manual / Honeywell**")
            barcode_manual = st.text_input("Barcode Value")
            if st.form_submit_button("SIMPAN DATA ✨") and barcode_manual:
                if save_data(barcode_manual, date_pick):
                    st.toast("✅ Tersimpan!")
                    time.sleep(1)
                    st.rerun()

    with col_right:
        st.markdown("### 📊 Mini Monitor")
        try:
            sheet_recap = sh.worksheet("Report Recap")
            # Mengambil data terbaru secara langsung
            raw_data = sheet_recap.get_all_values()
            
            if len(raw_data) > 0:
                # Pastikan header tersedia
                header = ["No", "Barcode", "Timestamp"]
                # Ambil hanya baris data (mulai baris ke-2) dan ambil kolom 1, 2, 3 saja
                rows = [r[:3] for r in raw_data[1:] if len(r) >= 2]
                
                if rows:
                    df = pd.DataFrame(rows, columns=header)
                    # REVERSE: Data terbaru di urutan 0 (paling atas)
                    df_reversed = df.iloc[::-1].reset_index(drop=True)
                    df_reversed.insert(0, "Pilih", False)

                    # Editor Tabel
                    edited_df = st.data_editor(
                        df_reversed.head(20), # Tampilkan 20 data terbaru
                        column_config={
                            "Pilih": st.column_config.CheckboxColumn(required=True),
                            "No": st.column_config.TextColumn(width="small"),
                            "Barcode": st.column_config.TextColumn(width="medium"),
                            "Timestamp": st.column_config.TextColumn(width="small")
                        },
                        disabled=["No", "Barcode", "Timestamp"],
                        hide_index=True,
                        use_container_width=True,
                        key="table_editor"
                    )

                    # Tombol Hapus
                    if st.button("🗑️ HAPUS DATA TERPILIH"):
                        selected_indices = edited_df[edited_df["Pilih"] == True].index.tolist()
                        if selected_indices:
                            total_rows_gsheet = len(raw_data)
                            # Hapus dari GSheet berdasarkan posisi asli
                            # Baris GSheet = total_rows - index_di_df_reversed
                            for idx in sorted(selected_indices, reverse=False):
                                row_to_del = total_rows_gsheet - idx
                                sheet_recap.delete_rows(int(row_to_del))
                            
                            st.toast("🗑️ Data Berhasil Dihapus!")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.info("Belum ada data di kolom A, B, C.")
            else:
                st.info("Sheet kosong.")
        except Exception as e:
            st.error(f"Gagal Load Tabel: {e}")

st.caption("Cinnamoroll Wahana System v5.1 - Fix Table Monitoring")
