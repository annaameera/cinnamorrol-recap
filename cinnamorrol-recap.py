import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Cinnamoroll Wahana Recap", page_icon="☁️", layout="wide")

# --- CUSTOM CSS: GLOSSY CINNAMOROLL THEME ---
st.markdown("""
    <style>
    /* Background Gradient Soft */
    .stApp {
        background: linear-gradient(135deg, #e0f2fe 0%, #ffffff 50%, #bae6fd 100%);
    }

    /* Judul Font Hitam Tegas */
    .main-title {
        color: #000000;
        font-family: 'Segoe UI', Roboto, sans-serif;
        font-weight: 800;
        text-align: center;
        font-size: 3rem;
        margin-bottom: 10px;
    }

    /* Efek Glossy pada Kontainer */
    div[data-testid="stForm"], .glossy-card {
        background: rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(15px) saturate(180%);
        -webkit-backdrop-filter: blur(15px) saturate(180%);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.7);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
        padding: 25px;
    }

    /* Tombol Glossy */
    .stButton>button {
        background: rgba(56, 189, 248, 0.8);
        color: white;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.4);
        font-weight: bold;
        transition: 0.3s;
        backdrop-filter: blur(5px);
    }

    .stButton>button:hover {
        background: rgba(2, 132, 199, 1);
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.5);
        color: white;
    }

    /* Table Styling */
    .stDataFrame {
        border-radius: 15px;
        background: rgba(255, 255, 255, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNGSI KONEKSI ---
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
        st.error(f"Koneksi Gagal: {e}")
        return None

sh = init_gsheet()

if sh:
    sheet_recap = sh.worksheet("Report Recap")
    
    st.markdown("<h1 class='main-title'>☁️ CINNAMOROLL RECAP</h1>", unsafe_allow_html=True)

    # --- INPUT SECTION ---
    with st.form("input_form", clear_on_submit=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            date_target = st.date_input("📅 Pilih Tanggal", datetime.now())
        with c2:
            barcode = st.text_input("📥 Sandbox (Scan Honeywell / Manual)", placeholder="Masukkan barcode...")
        
        submit = st.form_submit_button("SIMPAN DATA KE GSHEET 🎀")

    if submit and barcode:
        ts = datetime.now().strftime("%H:%M:%S")
        sheet_daily_name = date_target.strftime("%d_%m_%Y_Rekap Wahana")

        # --- LOGIKA UNIQUE DATA (B2:B1340) ---
        all_b_values = sheet_recap.col_values(2)[1:1340] # Ambil data B2:B1340
        
        if barcode in all_b_values:
            st.warning(f"Data '{barcode}' sudah ada! (Duplikat dicegah)")
        else:
            # 1. Update Report Recap
            next_row = len(sheet_recap.col_values(2)) + 1
            if next_row <= 1340:
                sheet_recap.update_acell(f'B{next_row}', barcode)
                sheet_recap.update_acell(f'C{next_row}', ts)
                
                # 2. Update Sheet Harian
                try:
                    ws_daily = sh.worksheet(sheet_daily_name)
                except gspread.WorksheetNotFound:
                    ws_daily = sh.add_worksheet(title=sheet_daily_name, rows="1000", cols="5")
                    ws_daily.append_row(["Data Barcode", "Timestamp"])
                
                ws_daily.append_row([barcode, ts])
                st.success(f"Data '{barcode}' berhasil ditambahkan!")
                st.rerun()

    # --- MONITOR & DELETE SECTION ---
    st.markdown("---")
    st.subheader("📊 Live Monitor & Data Management")

    # Ambil data terbaru
    raw_data = sheet_recap.get_all_values()
    if len(raw_data) > 1:
        df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
        
        # Tambahkan kolom checkbox untuk hapus
        df.insert(0, "Pilih (Hapus)", False)
        
        edited_df = st.data_editor(
            df,
            column_config={"Pilih (Hapus)": st.column_config.CheckboxColumn(required=True)},
            disabled=[c for c in df.columns if c != "Pilih (Hapus)"],
            hide_index=True,
            use_container_width=True,
            key="data_editor"
        )

        # Tombol Hapus Manual
        if st.button("🗑️ Hapus Baris Terpilih"):
            # Cari baris mana yang di-centang
            rows_to_delete = edited_df[edited_df["Pilih (Hapus)"] == True].index.tolist()
            
            if rows_to_delete:
                # Gspread delete rows (Urutan terbalik agar indeks tidak bergeser)
                for row_idx in sorted(rows_to_delete, reverse=True):
                    # +2 karena header gsheet index 1 dan dataframe index 0
                    sheet_recap.delete_rows(row_idx + 2)
                
                st.success(f"Berhasil menghapus {len(rows_to_delete)} baris!")
                st.rerun()
            else:
                st.info("Pilih baris dulu dengan menceklis tabel di atas.")
    else:
        st.info("Belum ada data tersedia.")

else:
    st.error("Pastikan 'gcp_service_account' sudah diatur di Secrets Streamlit Cloud!")
