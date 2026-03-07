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

# --- CONFIG ---
st.set_page_config(page_title="Wahana Recap", page_icon="☁️", layout="wide")

if 'recap_date' not in st.session_state:
    st.session_state['recap_date'] = datetime.now()

# --- CSS ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0ea5e9 0%, #e0f2fe 100%); }
    .main-title { color: #000; font-weight: 900; text-align: center; font-size: 2.5rem; }
    div[data-testid="stForm"] { background: rgba(255, 255, 255, 0.3); border-radius: 20px; }
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

# --- FUNGSI SIMPAN ---
def save_data(barcode_val, date_obj):
    if not barcode_val: return False
    try:
        ts = datetime.now().strftime("%H:%M:%S")
        sheet_daily_name = date_obj.strftime("%d_%m_%Y_Rekap Wahana")
        all_b = sheet_master.col_values(2)
        if barcode_val in all_b:
            st.toast(f"⚠️ DUPLIKAT: {barcode_val}", icon="⚠️")
            return False
        next_row = len(all_b) + 1
        sheet_master.update_acell(f'B{next_row}', barcode_val)
        sheet_master.update_acell(f'C{next_row}', ts)
        
        try:
            sh = sheet_master.spreadsheet
            ws_daily = sh.worksheet(sheet_daily_name)
        except gspread.WorksheetNotFound:
            ws_daily = sh.add_worksheet(title=sheet_daily_name, rows="1000", cols="5")
            ws_daily.append_row(["Barcode", "Timestamp"])
        ws_daily.append_row([barcode_val, ts])
        return True
    except Exception as e:
        st.error(f"Simpan Gagal: {e}")
        return False

# --- UI ---
if sheet_master:
    st.markdown("<h1 class='main-title'>☁️ WAHANA RECAP</h1>", unsafe_allow_html=True)
    col_in, col_tab = st.columns([1, 1.2])

    with col_in:
        date_pick = st.date_input("📅 TANGGAL", value=st.session_state['recap_date'])
        st.session_state['recap_date'] = date_pick
        
        def video_callback(frame):
            img = frame.to_ndarray(format="bgr24")
            for obj in decode(img):
                st.session_state['detected_now'] = obj.data.decode('utf-8')
            return frame.from_ndarray(img, format="bgr24")

        webrtc_streamer(key="scan", video_frame_callback=video_callback, 
                        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
                        media_stream_constraints={"video": True, "audio": False})

        if 'detected_now' in st.session_state:
            if save_data(st.session_state['detected_now'], date_pick):
                st.toast("✅ Scan Berhasil!")
                del st.session_state['detected_now']
                time.sleep(1)
                st.rerun()

        with st.form("manual", clear_on_submit=True):
            barcode_manual = st.text_input("Manual / Honeywell Input")
            if st.form_submit_button("SIMPAN ✨") and barcode_manual:
                if save_data(barcode_manual, date_pick):
                    st.toast("✅ Tersimpan!")
                    time.sleep(1)
                    st.rerun()

    with col_tab:
        st.markdown("### 📊 Recent Updates")
        try:
            # Ambil data murni
            raw_data = sheet_master.get_all_values()
            
            if len(raw_data) > 1:
                # 1. Buat DataFrame dengan 'Original Row Index' agar tidak salah hapus
                rows = []
                for i, r in enumerate(raw_data[1:]):
                    # i+2 karena: i mulai 0, +1 (untuk header), +1 (karena GSheet index mulai 1)
                    actual_row_num = i + 2 
                    content = (r + ["", "", ""])[:3]
                    rows.append([actual_row_num] + content)

                df = pd.DataFrame(rows, columns=["Gsheet_Row", "No", "Barcode", "Timestamp"])
                
                # 2. Reverse Tampilan (Terbaru di atas)
                df_view = df.iloc[::-1].reset_index(drop=True)
                df_view.insert(0, "Pilih", False)

                # 3. Tampilkan Editor (Sembunyikan Gsheet_Row dari User)
                edited_df = st.data_editor(
                    df_view.head(25),
                    column_config={
                        "Pilih": st.column_config.CheckboxColumn(required=True),
                        "Gsheet_Row": None, # Kolom ini disembunyikan
                        "No": st.column_config.TextColumn(width="small"),
                        "Barcode": st.column_config.TextColumn(width="medium"),
                    },
                    disabled=["No", "Barcode", "Timestamp"],
                    hide_index=True,
                    use_container_width=True,
                    key="editor_final"
                )

                # 4. Logika Hapus yang Aman
                if st.button("🗑️ HAPUS TERPILIH"):
                    selected_rows = edited_df[edited_df["Pilih"] == True]["Gsheet_Row"].tolist()
                    if selected_rows:
                        # Hapus dari indeks terbesar ke terkecil agar tidak terjadi pergeseran baris
                        for row_num in sorted(selected_rows, reverse=True):
                            sheet_master.delete_rows(int(row_num))
                        
                        st.toast(f"🗑️ {len(selected_rows)} Data Terhapus!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("Belum ada data di 'Report Recap'.")
        except Exception as e:
            st.error(f"Error Table: {e}")

st.caption("v5.4 - Row Mapping Fix for Delete")
