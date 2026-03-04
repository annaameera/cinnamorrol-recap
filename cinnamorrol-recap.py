import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Wahana Recap", page_icon="☁️", layout="wide")

# --- CUSTOM CSS: BLUE GLOSSY CRYSTAL THEME ---
st.markdown("""
    <style>
    /* Background Biru Langit Bergradasi */
    .stApp {
        background: linear-gradient(135deg, #0ea5e9 0%, #38bdf8 30%, #e0f2fe 100%);
        background-attachment: fixed;
    }

    /* Judul Utama Font Hitam Tegas */
    .main-title {
        color: #000000;
        font-family: 'Segoe UI', Tahoma, Geneva, sans-serif;
        font-weight: 900;
        text-align: center;
        font-size: 3.5rem;
        margin-bottom: 0px;
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    /* Container Glossy (Efek Kaca Kristal) */
    div[data-testid="stForm"], .glossy-card {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(20px) saturate(200%);
        -webkit-backdrop-filter: blur(20px) saturate(200%);
        border-radius: 30px;
        border: 1px solid rgba(255, 255, 255, 0.4);
        box-shadow: 0 15px 35px 0 rgba(0, 0, 0, 0.1);
        padding: 30px;
        color: #000000;
    }

    /* Input Box Glossy */
    .stTextInput>div>div>input {
        background: rgba(255, 255, 255, 0.6) !important;
        border-radius: 15px !important;
        border: 2px solid rgba(255, 255, 255, 0.8) !important;
        color: #000000 !important;
        font-weight: bold;
        font-size: 1.1rem;
    }

    /* Tombol Biru Glossy (Shining Effect) */
    .stButton>button {
        background: linear-gradient(135deg, #ffffff 0%, #bae6fd 100%);
        color: #0369a1 !important;
        border-radius: 50px;
        border: 1px solid rgba(255, 255, 255, 0.5);
        font-weight: 800;
        padding: 15px 40px;
        transition: all 0.3s ease-in-out;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        width: 100%;
        text-transform: uppercase;
    }

    .stButton>button:hover {
        transform: translateY(-3px) scale(1.02);
        background: #ffffff;
        box-shadow: 0 10px 25px rgba(255, 255, 255, 0.4);
        color: #0ea5e9 !important;
    }

    /* Table Styling (Range A,B,C) */
    .stDataFrame {
        background: rgba(255, 255, 255, 0.4);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.6);
    }
    
    /* Sidebar Glossy */
    [data-testid="stSidebar"] {
        background-color: rgba(14, 165, 233, 0.8);
        backdrop-filter: blur(10px);
    }
    </style>
    """, unsafe_allow_html=True)

# --- KONEKSI GSHEET (VIA SECRETS) ---
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

if sh:
    sheet_recap = sh.worksheet("Report Recap")
    
    st.markdown("<h1 class='main-title'>☁️ WAHANA RECAP</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#000000; font-weight:600;'>Recap Wahana</p>", unsafe_allow_html=True)

    # --- INPUT SECTION ---
    with st.form("main_scan_form", clear_on_submit=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            date_pick = st.date_input("📅 TANGGAL REKAP", datetime.now())
        with c2:
            barcode = st.text_input("📥 SANDBOX INPUT (Honeywell)", placeholder="Arahkan kursor & scan sekarang...")
        
        btn_submit = st.form_submit_button("SIMPAN DATA KE GSHEET ✨")

    if btn_submit:
        if not barcode:
            st.toast("Scan Gagal! Input Kosong.", icon="❌")
            st.error("❌ ERROR: Tidak ada data yang di-scan!")
        else:
            ts = datetime.now().strftime("%H:%M:%S")
            sheet_daily_name = date_pick.strftime("%d_%m_%Y_Rekap Wahana")

            # --- LOGIKA ANTI-DUPLIKAT (Kolom B2:B1340) ---
            all_b_values = sheet_recap.col_values(2)[1:1340]
            
            if barcode in all_b_values:
                st.toast(f"DUPLIKAT: {barcode}", icon="⚠️")
                st.warning(f"⚠️ DATA DUPLIKAT: Barcode '{barcode}' sudah pernah tersimpan!")
            else:
                try:
                    # 1. Update Report Recap (A, B, C)
                    next_row = len(sheet_recap.col_values(2)) + 1
                    if next_row <= 1340:
                        sheet_recap.update_acell(f'B{next_row}', barcode)
                        sheet_recap.update_acell(f'C{next_row}', ts)
                        
                        # 2. Update Sheet Harian (Dynamic Creation)
                        try:
                            ws_daily = sh.worksheet(sheet_daily_name)
                        except gspread.WorksheetNotFound:
                            ws_daily = sh.add_worksheet(title=sheet_daily_name, rows="1000", cols="5")
                            ws_daily.append_row(["Data Barcode", "Timestamp"])
                        
                        ws_daily.append_row([barcode, ts])
                        
                        # --- NOTIFIKASI SUKSES ---
                        st.toast(f"BERHASIL: {barcode}", icon="✅")
                        st.success(f"✅ BERHASIL: '{barcode}' telah diproses ke Cloud!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ LIMIT TERCAPAI: Sheet Report Recap sudah penuh (1340 baris)!")
                except Exception as e:
                    st.error(f"Gagal memproses data: {e}")

    # --- MINI MONITOR (KOLOM A, B, C) ---
    st.markdown("---")
    st.markdown("<h3 style='color:#000000;'>📊 Table</h3>", unsafe_allow_html=True)

    raw_data = sheet_recap.get_all_values()
    if len(raw_data) > 0:
        header = raw_data[0][:3] # Mengambil Kolom A, B, dan C
        # Memberikan nama jika header kosong di gsheet
        if not header[0]: header[0] = "No"
        if not header[1]: header[1] = "Data Barcode"
        if not header[2]: header[2] = "Timestamp"

        data_rows = [r[:3] for r in raw_data[1:] if len(r) >= 2]
        df = pd.DataFrame(data_rows, columns=header)
        df.insert(0, "Pilih", False)

        # Editor Tabel Glossy
        edited_df = st.data_editor(
            df.tail(15), 
            column_config={"Pilih": st.column_config.CheckboxColumn(required=True)},
            disabled=[c for c in df.columns if c != "Pilih"],
            hide_index=True,
            use_container_width=True,
            key="glossy_monitor"
        )

        if st.button("🗑️ HAPUS BARIS TERPILIH"):
            selected = edited_df[edited_df["Pilih"] == True].index.tolist()
            if selected:
                total_data = len(df)
                for idx in sorted(selected, reverse=True):
                    # Kalkulasi baris asli di gsheet
                    offset = max(0, total_data - 15)
                    row_gsheet = idx + offset + 2
                    sheet_recap.delete_rows(row_gsheet)
                
                st.toast("Data terhapus dari cloud!", icon="🗑️")
                st.rerun()
            else:
                st.info("Pilih data yang ingin dihapus dengan menekan centang.")
    else:
        st.info("Belum ada data terekam.")

else:
    st.error("Konfigurasi Secrets Gagal atau Belum Dipasang!")

st.caption("Cinnamoroll Wahana Inventory System v2.0 - Ultra Glossy")
