import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Cinnamoroll Wahana Recap", page_icon="☁️", layout="wide")

# --- CUSTOM CSS: ULTRA GLOSSY & GLASSMORPHISM ---
st.markdown("""
    <style>
    /* Background Animasi Biru Langit Soft */
    .stApp {
        background: linear-gradient(-45deg, #e0f2fe, #f0f9ff, #ffffff, #bae6fd);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
    }
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* Judul Font Hitam Elegan */
    .main-title {
        color: #000000;
        font-family: 'Segoe UI', Tahoma, Geneva, sans-serif;
        font-weight: 900;
        text-align: center;
        font-size: 3rem;
        letter-spacing: -1px;
        margin-bottom: 5px;
    }

    /* Container Glossy (Efek Kaca) */
    div[data-testid="stForm"], .glossy-card {
        background: rgba(255, 255, 255, 0.25);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border-radius: 30px;
        border: 1px solid rgba(255, 255, 255, 0.5);
        box-shadow: 0 10px 40px 0 rgba(31, 38, 135, 0.1);
        padding: 30px;
    }

    /* Input Box Glossy */
    .stTextInput>div>div>input {
        background: rgba(255, 255, 255, 0.5) !important;
        border-radius: 15px !important;
        border: 1px solid rgba(125, 211, 252, 0.5) !important;
        color: #0c4a6e !important;
        font-weight: 600;
    }

    /* Tombol Biru Glossy Berkilo */
    .stButton>button {
        background: linear-gradient(135deg, #7dd3fc 0%, #0ea5e9 100%);
        color: white;
        border-radius: 50px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        font-weight: bold;
        padding: 15px 30px;
        transition: all 0.4s ease;
        box-shadow: 0 4px 15px rgba(14, 165, 233, 0.3);
        width: 100%;
    }

    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(14, 165, 233, 0.5);
        background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%);
        color: white;
    }

    /* Table Styling */
    .stDataFrame {
        background: rgba(255, 255, 255, 0.3);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.5);
    }
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
        st.error(f"Koneksi Gagal: {e}")
        return None

sh = init_gsheet()

if sh:
    sheet_recap = sh.worksheet("Report Recap")
    
    st.markdown("<h1 class='main-title'>☁️ CINNAMOROLL RECAP</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#64748b; font-weight:500;'>Wahana Inventory System - Premium Glossy Mode</p>", unsafe_allow_html=True)

    # --- INPUT SECTION ---
    with st.form("scan_form", clear_on_submit=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            date_pick = st.date_input("📅 Tanggal Rekap", datetime.now())
        with c2:
            barcode = st.text_input("📥 Kotak Sandbox (Honeywell)", placeholder="Arahkan kursor & scan...")
        
        btn_submit = st.form_submit_button("SIMPAN DATA SEKARANG ✨")

    if btn_submit:
        if not barcode:
            st.toast("Gagal! Scan tidak terdeteksi.", icon="❌")
            st.error("❌ Scan Gagal: Kotak input kosong!")
        else:
            ts = datetime.now().strftime("%H:%M:%S")
            sheet_daily_name = date_pick.strftime("%d_%m_%Y_Rekap Wahana")

            # --- LOGIKA UNIQUE DATA (B2:B1340) ---
            all_b = sheet_recap.col_values(2)[1:1340] 
            
            if barcode in all_b:
                st.toast(f"Duplikat: {barcode}", icon="⚠️")
                st.warning(f"⚠️ Scan Duplikat: Data '{barcode}' sudah ada di sistem!")
            else:
                try:
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
                        
                        # --- NOTIFIKASI SUKSES ---
                        st.toast(f"Berhasil! {barcode} tersimpan.", icon="✅")
                        st.success(f"✅ Berhasil: '{barcode}' masuk ke cloud!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Kapasitas Penuh (B1340)!")
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- MONITOR MONITOR TABEL (A, B, C) ---
    st.markdown("---")
    st.subheader("📊 Live Monitor: Kolom A, B, C")

    raw_rows = sheet_recap.get_all_values()
    if len(raw_rows) > 0:
        header = raw_rows[0][:3]
        data_body = [r[:3] for r in raw_rows[1:] if len(r) >= 2]
        df = pd.DataFrame(data_body, columns=header)
        df.insert(0, "Pilih", False)

        edited_df = st.data_editor(
            df.tail(15), 
            column_config={"Pilih": st.column_config.CheckboxColumn(required=True)},
            disabled=[c for c in df.columns if c != "Pilih"],
            hide_index=True,
            use_container_width=True,
            key="table_monitor"
        )

        if st.button("🗑️ Hapus Baris Terpilih"):
            selected_rows = edited_df[edited_df["Pilih"] == True].index.tolist()
            if selected_rows:
                total_rows = len(df)
                for idx in sorted(selected_rows, reverse=True):
                    offset = max(0, total_rows - 15)
                    row_to_del = idx + offset + 2
                    sheet_recap.delete_rows(row_to_del)
                
                st.toast("Data terhapus!", icon="🗑️")
                st.rerun()
            else:
                st.info("Ceklist data untuk dihapus.")
    else:
        st.info("Menunggu data masuk...")

else:
    st.error("Konfigurasi Secrets Gagal!")
