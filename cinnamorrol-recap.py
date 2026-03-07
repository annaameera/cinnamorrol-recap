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

# --- KONEKSI GSHEET ---
@st.cache_resource
def init_gsheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        url = "https://docs.google.com/spreadsheets/d/1vlwLdTxPLDnDkrn4luNKnRr_SH5TG-YJXK5NZAdWCVQ/edit?usp=sharing"
        return client.open_by_url(url)
    except Exception as e:
        st.error(f"Koneksi Cloud Terputus: {e}")
        return None

sh = init_gsheet()

# --- FUNGSI INTI: SIMPAN DATA ---
def save_data(barcode_val, date_obj):
    if not barcode_val: return
    try:
        sheet_recap = sh.worksheet("Report Recap")
        ts = datetime.now().strftime("%H:%M:%S")
        sheet_daily_name = date_obj.strftime("%d_%m_%Y_Rekap Wahana")
        
        # Logika Anti-Duplikat (Cek kolom B)
        all_b = sheet_recap.col_values(2)
        if barcode_val in all_b:
            st.warning(f"⚠️ DATA DUPLIKAT: {barcode_val} sudah terdaftar!")
            return False

        # 1. Update Report Recap (Master)
        next_row = len(all_b) + 1
        sheet_recap.update_acell(f'B{next_row}', barcode_val)
        sheet_recap.update_acell(f'C{next_row}', ts)
        
        # 2. Update Sheet Harian
        try:
            ws_daily = sh.worksheet(sheet_daily_name)
        except gspread.WorksheetNotFound:
            ws_daily = sh.add_worksheet(title=sheet_daily_name, rows="1000", cols="5")
            ws_daily.append_row(["Barcode", "Timestamp"])
        
        ws_daily.append_row([barcode_val, ts])
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# --- UI UTAMA ---
if sh:
    st.markdown("<h1 class='main-title'>☁️ WAHANA RECAP</h1>", unsafe_allow_html=True)
    
    col_input, col_table = st.columns([1, 1.2])

    with col_input:
        st.markdown("### 📥 Input Panel")
        
        # 1. Tanggal (Persistent)
        date_pick = st.date_input("📅 TANGGAL REKAP", value=st.session_state['recap_date'])
        st.session_state['recap_date'] = date_pick
        
        # 2. Scanner Kamera (Auto-Enter)
        st.write("📸 **Auto-Scan Camera**")
        def video_callback(frame):
            img = frame.to_ndarray(format="bgr24")
            decoded = decode(img)
            for obj in decoded:
                data = obj.data.decode('utf-8')
                st.session_state['detected_now'] = data
                # Feedback visual
                pts = np.array([obj.polygon], np.int32)
                cv2.polylines(img, [pts], True, (0, 255, 0), 3)
            return frame.from_ndarray(img, format="bgr24")

        webrtc_streamer(
            key="scanner",
            video_frame_callback=video_callback,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": True, "audio": False}
        )

        # Proses hasil scan otomatis
        if 'detected_now' in st.session_state:
            res = save_data(st.session_state['detected_now'], date_pick)
            if res:
                st.toast(f"✅ Auto-Scan Berhasil: {st.session_state['detected_now']}")
                del st.session_state['detected_now']
                time.sleep(1)
                st.rerun()

        # 3. Input Manual (Honeywell / Keyboard)
        with st.form("manual_form", clear_on_submit=True):
            st.write("⌨️ **Input Manual / Scanner Honeywell**")
            barcode_manual = st.text_input("Barcode Value", placeholder="Ketik atau scan di sini...")
            btn_manual = st.form_submit_button("SIMPAN MANUAL ✨")
            
            if btn_manual and barcode_manual:
                if save_data(barcode_manual, date_pick):
                    st.toast(f"✅ Berhasil Simpan: {barcode_manual}")
                    time.sleep(1)
                    st.rerun()

    with col_table:
        st.markdown("### 📊 Recent Updates")
        try:
            sheet_recap = sh.worksheet("Report Recap")
            raw_data = sheet_recap.get_all_values()
            
            if len(raw_data) > 1:
                # Ambil Kolom A, B, C (No, Barcode, Timestamp)
                header = ["No", "Data Barcode", "Timestamp"]
                data_rows = [r[:3] for r in raw_data[1:] if len(r) >= 2]
                
                df = pd.DataFrame(data_rows, columns=header)
                # Balik urutan: Data terbaru di atas
                df_reversed = df.iloc[::-1].reset_index(drop=True)
                # Tambah kolom Checkbox untuk hapus
                df_reversed.insert(0, "Pilih", False)

                edited_df = st.data_editor(
                    df_reversed.head(15), 
                    column_config={"Pilih": st.column_config.CheckboxColumn(required=True)},
                    disabled=["No", "Data Barcode", "Timestamp"],
                    hide_index=True,
                    use_container_width=True,
                    key="editor_recap"
                )

                if st.button("🗑️ HAPUS DATA TERPILIH"):
                    selected_indices = edited_df[edited_df["Pilih"] == True].index.tolist()
                    if selected_indices:
                        total_rows_gsheet = len(raw_data)
                        # Hapus dari baris terbawah agar indeks tidak bergeser
                        for idx in sorted(selected_indices, reverse=False):
                            # Baris GSheet = Total - Index di DF Reversed
                            row_to_del = total_rows_gsheet - idx
                            sheet_recap.delete_rows(int(row_to_del))
                        
                        st.toast("🗑️ Data telah dihapus dari Cloud!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("Belum ada data terekam.")
        except Exception as e:
            st.error(f"Gagal memuat tabel: {e}")

st.caption("Cinnamoroll Wahana System v5.0 - Hybrid Scanner & Manual")
