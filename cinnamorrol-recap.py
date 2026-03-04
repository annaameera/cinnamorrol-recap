import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Cinnamoroll Dashboard", page_icon="☁️")

# CSS Tema Cinnamoroll
st.markdown("""
    <style>
    .stApp { background-color: #F0F8FF; }
    .stButton>button { background-color: #A0D8EF; color: white; border-radius: 20px; }
    h1 { color: #5FB0E8; font-family: 'Comic Sans MS'; }
    </style>
    """, unsafe_allow_html=True)

# --- KONEKSI GSHEET VIA SECRETS ---
def init_gsheet():
    # Mengambil kredensial dari Streamlit Secrets (bukan file JSON)
    creds_dict = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    url = "https://docs.google.com/spreadsheets/d/1vlwLdTxPLDnDkrn4luNKnRr_SH5TG-YJXK5NZAdWCVQ/edit?usp=sharing"
    return client.open_by_url(url)

try:
    sh = init_gsheet()
    sheet_recap = sh.worksheet("Report Recap")
except Exception as e:
    st.error(f"Koneksi Gagal: {e}")
    st.stop()

# --- UI DASHBOARD ---
st.title("☁️ Cinnamoroll Wahana Recap ☁️")

# Input Tanggal (Kalender)
selected_date = st.date_input("📅 Pilih Tanggal", datetime.now())
suffix_name = selected_date.strftime("%d_%m_%Y_Rekap Wahana")

# Sandbox & Manual Input
user_input = st.text_input("Input Barcode / Manual", placeholder="Scan di sini...")

if st.button("Simpan Data 🎀"):
    if user_input:
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 1. Update ke Report Recap (Kolom B & C)
        next_row = len(sheet_recap.col_values(2)) + 1
        sheet_recap.update_acell(f'B{next_row}', user_input)
        sheet_recap.update_acell(f'C{next_row}', timestamp)
        
        # 2. Update/Buat Sheet Baru sesuai Tanggal
        try:
            target_sh = sh.worksheet(suffix_name)
        except:
            target_sh = sh.add_worksheet(title=suffix_name, rows="1000", cols="5")
            target_sh.append_row(["Data", "Timestamp"])
        
        target_sh.append_row([user_input, timestamp])
        st.success("Berhasil tersimpan ke Cloud!")

# --- DISPLAY DATA ---
st.divider()
st.subheader("📋 Preview Data")
data = sheet_recap.get_all_values()
if len(data) > 1:
    df = pd.DataFrame(data[1:], columns=data[0])
    st.dataframe(df.tail(10), use_container_width=True)
