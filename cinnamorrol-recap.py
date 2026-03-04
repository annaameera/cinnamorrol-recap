import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Cinnamoroll Wahana Recap", page_icon="☁️", layout="wide")

# Custom CSS: Tema Cinnamoroll (Biru Pastel, Putih, Border Melengkung)
st.markdown("""
    <style>
    .stApp { background-color: #F0F8FF; }
    .stButton>button { 
        background-color: #A0D8EF; color: white; border-radius: 20px; 
        border: 2px solid #5FB0E8; width: 100%; font-weight: bold;
    }
    .stTextInput>div>div>input { border-radius: 15px; border: 2px solid #A0D8EF; }
    h1, h2, h3 { color: #5FB0E8; font-family: 'Comic Sans MS', cursive, sans-serif; text-align: center; }
    .stDataFrame { border: 2px solid #A0D8EF; border-radius: 10px; background: white; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNGSI KONEKSI (MENGGUNAKAN SECRETS) ---
@st.cache_resource
def init_gsheet():
    # Mengambil kredensial dari Streamlit Secrets (Format TOML/JSON)
    creds_info = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
    client = gspread.authorize(creds)
    url = "https://docs.google.com/spreadsheets/d/1vlwLdTxPLDnDkrn4luNKnRr_SH5TG-YJXK5NZAdWCVQ/edit?usp=sharing"
    return client.open_by_url(url)

try:
    sh = init_gsheet()
    sheet_recap = sh.worksheet("Report Recap")
except Exception as e:
    st.error(f"Aduh! Cinnamoroll gagal terhubung ke awan: {e}")
    st.stop()

# --- SIDEBAR & FILTER ---
with st.sidebar:
    st.image("https://raw.githubusercontent.com/r6-y6/assets/main/cinnamoroll.png", width=150) # Ganti URL image jika punya
    st.title("Settings 🎀")
    selected_date = st.date_input("Pilih Tanggal Rekap", datetime.now())
    # Format Nama Sheet: 04_03_2026_Rekap Wahana
    target_sheet_name = f"{selected_date.strftime('%d_%m_%Y')}_Rekap Wahana"

# --- MAIN DASHBOARD ---
st.title("☁️ Cinnamoroll Wahana Recap ☁️")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📥 Input Data")
    # Sandbox untuk Barcode Honeywell atau Manual
    barcode_input = st.text_input("Scan Barcode / Input Manual:", key="sandbox", placeholder="Arahkan kursor & scan...")
    
    btn_save = st.button("Simpan ke GSheet ✨")

if btn_save and barcode_input:
    now_time = datetime.now().strftime("%H:%M:%S")
    
    # 1. Update ke 'Report Recap'
    # Mencari baris kosong di kolom B (B2:B1340)
    col_b_values = sheet_recap.col_values(2)
    next_row = len(col_b_values) + 1
    
    if next_row <= 1340:
        sheet_recap.update_acell(f'B{next_row}', barcode_input)
        sheet_recap.update_acell(f'C{next_row}', now_time) # Timestamp di Kolom C
        
        # Logika tambahan untuk kolom E & F jika diperlukan
        # sheet_recap.update_acell(f'F{next_row}', now_time) if ...
        
        # 2. Simpan ke Sheet Baru sesuai Tanggal
        try:
            ws_target = sh.worksheet(target_sheet_name)
        except gspread.WorksheetNotFound:
            ws_target = sh.add_worksheet(title=target_sheet_name, rows="1000", cols="5")
            ws_target.append_row(["Data Barcode", "Timestamp", "Status"])
        
        ws_target.append_row([barcode_input, now_time, "OK"])
        st.success(f"Data '{barcode_input}' berhasil dipeluk Cinnamoroll! (Tersimpan)")
    else:
        st.error("Waduh, Sheet 'Report Recap' sudah penuh sampai baris 1340!")

# --- DISPLAY & DELETE SECTION ---
st.divider()
st.subheader("📊 Mini GSheet View (Report Recap)")

# Ambil data terbaru (15 baris terakhir agar ringan)
data_raw = sheet_recap.get_all_values()
if len(data_raw) > 1:
    df = pd.DataFrame(data_raw[1:], columns=data_raw[0])
    
    # Tampilkan tabel yang bisa diedit (Checkbox simulasi hapus)
    df_with_select = df.copy()
    df_with_select.insert(0, "Pilih", False)
    
    edited_df = st.data_editor(
        df_with_select.tail(20), 
        column_config={"Pilih": st.column_config.CheckboxColumn(required=True)},
        disabled=df.columns,
        hide_index=True,
        use_container_width=True
    )
    
    if st.button("Hapus Data Terpilih 🗑️"):
        st.warning("Fitur hapus di GSheet memerlukan sinkronisasi baris yang presisi. Gunakan manual di GSheet jika data krusial.")
else:
    st.info("Belum ada data yang terekam hari ini.")

st.caption("Dashboard Created with ❤️ for Wahana Inventory")
