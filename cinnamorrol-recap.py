import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Cinnamoroll Wahana Recap", page_icon="☁️", layout="wide")

# --- CUSTOM CSS: THEMA BIRU ELEGAN & CINNAMOROLL ---
st.markdown("""
    <style>
    /* Mengubah background utama dengan gradasi biru elegan */
    .stApp {
        background: linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 100%);
    }

    /* Styling Header/Judul */
    h1 {
        color: #0369a1;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 800;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        padding-bottom: 20px;
    }

    /* Kotak Input & Kontainer (Glassmorphism Effect) */
    div[data-testid="stVerticalBlock"] > div:has(div.stTextInput) {
        background: rgba(255, 255, 255, 0.6);
        backdrop-filter: blur(10px);
        border-radius: 25px;
        padding: 30px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
    }

    /* Tombol Biru Elegan */
    .stButton>button {
        background: linear-gradient(90deg, #38bdf8 0%, #0284c7 100%);
        color: white;
        border-radius: 50px;
        border: none;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(2, 132, 199, 0.3);
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(2, 132, 199, 0.4);
        color: #f0f9ff;
    }

    /* Styling Dataframe/Table */
    .stDataFrame {
        border-radius: 20px;
        overflow: hidden;
        border: 2px solid #bae6fd;
    }

    /* Sidebar Customization */
    [data-testid="stSidebar"] {
        background-color: #f0f9ff;
        border-right: 2px solid #e0f2fe;
    }

    /* Label Styling */
    .stMarkdown p {
        color: #0c4a6e;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNGSI KONEKSI (MENGGUNAKAN SECRETS) ---
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
        st.error(f"❌ Koneksi Gagal: {e}")
        return None

sh = init_gsheet()

if sh:
    sheet_recap = sh.worksheet("Report Recap")
    
    # --- UI DASHBOARD ---
    st.markdown("<h1>☁️ CINNAMOROLL WAHANA SYSTEM</h1>", unsafe_allow_html=True)
    
    # Bagian Atas: Kalender & Input
    col_left, col_right = st.columns([1, 2], gap="large")
    
    with col_left:
        st.markdown("### 📅 Pengaturan Rekap")
        selected_date = st.date_input("Pilih Tanggal", datetime.now())
        # Format nama sheet sesuai permintaan
        sheet_name_new = selected_date.strftime("%d_%m_%Y_Rekap Wahana")
        st.info(f"Target: `{sheet_name_new}`")

    with col_right:
        st.markdown("### 📥 Sandbox Input")
        barcode_input = st.text_input("Arahkan kursor di sini untuk scan Honeywell", 
                                     placeholder="Menunggu scan barcode...", 
                                     key="main_input")
        
        btn_save = st.button("PROSES & SIMPAN DATA 🎀")

    # --- LOGIKA PENYIMPANAN ---
    if btn_save and barcode_input:
        ts = datetime.now().strftime("%H:%M:%S")
        
        # 1. Update ke Report Recap (B2:B1340)
        # Ambil kolom B untuk cari baris kosong
        b_col = sheet_recap.col_values(2)
        target_row = len(b_col) + 1
        
        if target_row <= 1340:
            # Update Data di B & Timestamp di C
            sheet_recap.update_acell(f'B{target_row}', barcode_input)
            sheet_recap.update_acell(f'C{target_row}', ts)
            
            # 2. Update ke Sheet Harian (Buat jika belum ada)
            try:
                ws_daily = sh.worksheet(sheet_name_new)
            except gspread.WorksheetNotFound:
                ws_daily = sh.add_worksheet(title=sheet_name_new, rows="1000", cols="5")
                ws_daily.append_row(["Data Barcode", "Timestamp"])
            
            ws_daily.append_row([barcode_input, ts])
            
            st.balloons()
            st.success(f"Berhasil disimpan ke baris {target_row}!")
        else:
            st.error("⚠️ Batas maksimal baris (1340) telah tercapai!")

    # --- TABEL VIEW ---
    st.markdown("---")
    st.markdown("### 📊 Live Monitor: Report Recap")
    
    data_raw = sheet_recap.get_all_values()
    if len(data_raw) > 1:
        df = pd.DataFrame(data_raw[1:], columns=data_raw[0])
        
        # Menampilkan tabel mini (20 data terakhir)
        st.dataframe(df.tail(20), use_container_width=True)
        
        # Opsi Hapus (Manual check)
        st.markdown("*(Gunakan Google Sheets secara langsung untuk menghapus baris demi akurasi data)*")
    else:
        st.info("Belum ada data di cloud.")

else:
    st.warning("Silakan periksa konfigurasi Secrets di Streamlit Cloud kamu.")
