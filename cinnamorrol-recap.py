import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Cinnamoroll Wahana Recap", page_icon="☁️", layout="wide")

# --- CUSTOM CSS: THEME BIRU ELEGAN ---
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #eef2ff 0%, #e0f2fe 100%); }
    h1 { color: #0369a1; font-family: 'Trebuchet MS'; font-weight: 800; text-align: center; }
    .stButton>button { 
        background: linear-gradient(90deg, #38bdf8 0%, #0284c7 100%); 
        color: white; border-radius: 50px; border: none; font-weight: 600;
    }
    div[data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.4);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 20px;
        border: 1px solid #bae6fd;
    }
    /* Mengatur tampilan tabel agar lebih bersih */
    .stDataFrame { border: 1px solid #bae6fd; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNGSI KONEKSI ---
@st.cache_resource
def init_gsheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Menggunakan st.secrets untuk deployment GitHub
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        url = "https://docs.google.com/spreadsheets/d/1vlwLdTxPLDnDkrn4luNKnRr_SH5TG-YJXK5NZAdWCVQ/edit?usp=sharing"
        return client.open_by_url(url)
    except Exception as e:
        st.error(f"Gagal koneksi ke Google Sheets: {e}")
        return None

sh = init_gsheet()

if sh:
    try:
        sheet_recap = sh.worksheet("Report Recap")
    except Exception:
        st.error("Sheet 'Report Recap' tidak ditemukan!")
        st.stop()

    st.markdown("<h1>☁️ CINNAMOROLL RECAP SYSTEM</h1>", unsafe_allow_html=True)

    # --- BAGIAN INPUT ---
    with st.form("input_form", clear_on_submit=True):
        col_a, col_b = st.columns([1, 2])
        with col_a:
            selected_date = st.date_input("📅 Tanggal Rekap", datetime.now())
        with col_b:
            barcode_input = st.text_input("📥 Sandbox Input (Honeywell/Manual)", placeholder="Scan barcode di sini...")
        
        submit_btn = st.form_submit_button("SIMPAN DATA KE CLOUD 🎀")

    if submit_btn and barcode_input:
        ts = datetime.now().strftime("%H:%M:%S")
        sheet_name_daily = selected_date.strftime("%d_%m_%Y_Rekap Wahana")
        
        # 1. Update Report Recap (Cari baris kosong di kolom B)
        # Ambil kolom B saja untuk efisiensi
        col_b_data = sheet_recap.col_values(2)
        next_row = len(col_b_data) + 1
        
        if next_row <= 1340:
            sheet_recap.update_acell(f'B{next_row}', barcode_input)
            sheet_recap.update_acell(f'C{next_row}', ts)
            
            # 2. Update Sheet Harian
            try:
                ws_daily = sh.worksheet(sheet_name_daily)
            except gspread.WorksheetNotFound:
                ws_daily = sh.add_worksheet(title=sheet_name_daily, rows="1000", cols="5")
                ws_daily.append_row(["Data Barcode", "Timestamp"])
            
            ws_daily.append_row([barcode_input, ts])
            st.success(f"✅ Data '{barcode_input}' tersimpan!")
            st.rerun() # Refresh untuk update tabel monitor
        else:
            st.error("Batas baris B1340 tercapai!")

    # --- LIVE MONITOR (FIX ERROR DI SINI) ---
    st.markdown("---")
    st.markdown("### 📊 Live Monitor: Report Recap")
    
    try:
        # Mengambil data dengan get_all_records() lebih aman untuk DataFrame
        # Jika sheet kosong, kita handle agar tidak error
        raw_rows = sheet_recap.get_all_values()
        
        if len(raw_rows) > 1:
            # Memastikan semua baris punya panjang yang sama dengan header
            header = raw_rows[0]
            data_body = [r for r in raw_rows[1:] if any(r)] # Hanya ambil baris yang ada isinya
            
            df = pd.DataFrame(data_body, columns=header)
            
            # Tambahkan kolom Delete (Checkbox)
            df.insert(0, "Pilih", False)
            
            # Tampilkan 15 data terbaru
            edited_df = st.data_editor(
                df.tail(15),
                column_config={"Pilih": st.column_config.CheckboxColumn(required=True)},
                disabled=[c for c in df.columns if c != "Pilih"],
                hide_index=True,
                use_container_width=True
            )
            
            if st.button("🗑️ Hapus Baris Terpilih"):
                st.warning("Untuk alasan keamanan cloud, penghapusan baris disarankan dilakukan langsung di Google Sheets.")
        else:
            st.info("💡 Belum ada data untuk ditampilkan.")
            
    except Exception as e:
        st.error(f"Gagal memuat tabel: {e}")
        st.info("Tips: Pastikan baris pertama di Google Sheets adalah Header (Judul Kolom).")

else:
    st.warning("Menunggu konfigurasi Secrets di Streamlit Cloud...")
