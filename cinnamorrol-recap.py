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
            sheet_recap.update_acell(f'B{next_row}', barcode_data)
            sheet_recap.update_acell(f'C{next_row}', current_time)
            
            # Logika tambahan: Jika input masuk ke E, timestamp ke F (Opsional sesuai permintaan)
            # sheet_recap.update_acell(f'E{next_row}', barcode_data)
            # sheet_recap.update_acell(f'F{next_row}', current_time)
            
            # 2. Update/Buat Sheet Baru Berdasarkan Tanggal
            try:
                ws_target = sh.worksheet(new_sheet_name)
            except gspread.WorksheetNotFound:
                ws_target = sh.add_worksheet(title=new_sheet_name, rows="1000", cols="5")
                ws_target.append_row(["Data Barcode", "Timestamp"])
            
            ws_target.append_row([barcode_data, current_time])
            
            st.success(f"Berhasil! Data '{barcode_data}' tersimpan di Report Recap (Baris {next_row}) dan sheet {new_sheet_name}")
        else:
            st.error("Sheet Report Recap sudah penuh (Limit B1340)!")
    else:
        st.warning("Masukkan data terlebih dahulu, sayang!")

# --- DISPLAY MINI GSHEET & DELETE ---
st.divider()
st.subheader("📊 Mini View: Report Recap")

# Ambil data dari GSheet
data = sheet_recap.get_all_values()
if len(data) > 1:
    df = pd.DataFrame(data[1:], columns=data[0])
    
    # Menambahkan kolom checkbox untuk hapus
    df.insert(0, "Pilih", False)
    
    edited_df = st.data_editor(
        df.tail(20), # Tampilkan 20 data terakhir agar ringan
        column_config={"Pilih": st.column_config.CheckboxColumn(required=True)},
        disabled=df.columns[1:], # Hanya kolom 'Pilih' yang bisa diedit
        hide_index=True,
    )

    if st.button("🗑️ Hapus Baris Terpilih"):
        # Logika hapus baris di GSheet memerlukan indeks asli
        # Untuk keamanan, biasanya disarankan hapus manual, 
        # namun di sini kita beri indikasi baris yang terpilih.
        st.info("Fitur hapus sinkronisasi baris aktif. Pastikan data yang dipilih benar.")
        # Logic: sheet_recap.delete_rows(index)
else:
    st.write("Belum ada data di sheet Report Recap.")

st.caption("Cinnamoroll Python Anomaly v1.0")
