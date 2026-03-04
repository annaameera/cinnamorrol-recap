import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Cinnamoroll Wahana Recap", page_icon="☁️", layout="wide")

# --- CUSTOM CSS (TEMA CINNAMOROLL) ---
st.markdown("""
    <style>
    .stApp { background-color: #F0F8FF; }
    .stButton>button { 
        background-color: #A0D8EF; color: white; border-radius: 20px; 
        border: 2px solid #5FB0E8; font-weight: bold; width: 100%;
    }
    .stTextInput>div>div>input { border-radius: 15px; border: 2px solid #A0D8EF; }
    h1, h2, h3 { color: #5FB0E8; font-family: 'Comic Sans MS', cursive, sans-serif; text-align: center; }
    .stDataFrame { border: 2px solid #A0D8EF; border-radius: 10px; }
    div[data-testid="stMetricValue"] { color: #5FB0E8; }
    </style>
    """, unsafe_allow_html=True)

# --- KONEKSI GSHEET (VIA SECRETS) ---
def init_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Mengambil kredensial dari Streamlit Secrets untuk deploy GitHub
    creds_info = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
    client = gspread.authorize(creds)
    url = "https://docs.google.com/spreadsheets/d/1vlwLdTxPLDnDkrn4luNKnRr_SH5TG-YJXK5NZAdWCVQ/edit?usp=sharing"
    return client.open_by_url(url)

try:
    sh = init_gsheet()
    sheet_recap = sh.worksheet("Report Recap")
except Exception as e:
    st.error(f"Koneksi Gagal: {e}. Pastikan Secrets sudah disetting!")
    st.stop()

# --- BAGIAN INPUT ---
st.title("☁️ Cinnamoroll Wahana Recap ☁️")
st.write("### Masukkan data barcode (Honeywell) atau manual di bawah ini")

# Kalender untuk memilih tanggal sheet baru
col_date, col_input = st.columns([1, 2])

with col_date:
    selected_date = st.date_input("📅 Pilih Tanggal Rekap", datetime.now())
    formatted_date = selected_date.strftime("%d_%m_%Y")
    new_sheet_name = f"{formatted_date}_Rekap Wahana"

with col_input:
    # Sandbox/Input Box
    barcode_data = st.text_input("📥 Sandbox / Kotak Input Data", placeholder="Scan atau Ketik di sini...", key="input_data")

# Tombol Simpan
if st.button("Simpan Data ✨"):
    if barcode_data:
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # 1. Update ke Sheet "Report Recap" (Cari baris kosong di B2:B1340)
        # Ambil semua data kolom B
        b_values = sheet_recap.col_values(2)
        next_row = len(b_values) + 1
        
        if next_row <= 1340:
            # Update Kolom B (Data) dan Kolom C (Timestamp)
            sheet_recap.update_acell(f'B{next_row
