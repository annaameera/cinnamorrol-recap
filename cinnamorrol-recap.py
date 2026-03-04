import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Wahana Recap", page_icon="☁️", layout="wide")

# --- SIDEBAR SETTINGS (SWITCH THEME) ---
with st.sidebar:
    st.title("Settings 🎀")
    theme_choice = st.radio("Pilih Tampilan Dashboard:", ["Glossy Theme", "Simple Mode"])
    st.divider()
    selected_date = st.date_input("📅 Tanggal Rekap", datetime.now())

# --- CUSTOM CSS: HANYA AKTIF JIKA PILIH GLOSSY ---
if theme_choice == "Glossy Theme":
    st.markdown("""
        <style>
        .stApp { background: linear-gradient(135deg, #0ea5e9 0%, #38bdf8 30%, #e0f2fe 100%); background-attachment: fixed; }
        .main-title { color: #000000; font-family: 'Segoe UI', sans-serif; font-weight: 900; text-align: center; font-size: 3rem; text-transform: uppercase; }
        div[data-testid="stForm"], .glossy-card {
            background: rgba(255, 255, 255, 0.25); backdrop-filter: blur(20px);
            border-radius: 30px; border: 1px solid rgba(255, 255, 255, 0.4);
            box-shadow: 0 15px 35px 0 rgba(0, 0, 0, 0.1); padding: 25px;
        }
        .stButton>button {
            background: linear-gradient(135deg, #ffffff 0%, #bae6fd 100%);
            color: #0369a1 !important; border-radius: 50px; font-weight: 800;
        }
        .stButton>button:hover { transform: scale(1.02); background: #ffffff; color: #0ea5e9 !important; }
        </style>
        """, unsafe_allow_html=True)
else:
    # Mode Sederhana: Hanya styling minimal agar judul tetap hitam
    st.markdown("""<style>.main-title { color: #000000; text-align: center; font-weight: bold; }</style>""", unsafe_allow_html=True)

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
        st.error(f"Koneksi Gagal: {e}")
        return None

sh = init_gsheet()

if sh:
    sheet_recap = sh.worksheet("Report Recap")
    st.markdown("<h1 class='main-title'>☁️ RECAP</h1>", unsafe_allow_html=True)

    # --- INPUT SECTION ---
    # Menggunakan container agar mode glossy bisa membungkus form
    with st.container():
        with st.form("input_form", clear_on_submit=True):
            barcode = st.text_input("📥 SANDBOX INPUT (Scan Barcode Honeywell)", placeholder="Scan di sini...")
            btn_submit = st.form_submit_button("SIMPAN DATA KE GSHEET ✨")

    if btn_submit:
        if not barcode:
            st.toast("Scan Gagal! Input Kosong.", icon="❌")
        else:
            ts = datetime.now().strftime("%H:%M:%S")
            sheet_daily_name = selected_date.strftime("%d_%m_%Y_Rekap Wahana")

            # --- LOGIKA UNIQUE DATA (B2:B1340) ---
            all_b_values = sheet_recap.col_values(2)[1:1340]
            
            if barcode in all_b_values:
                st.toast(f"DUPLIKAT: {barcode}", icon="⚠️")
                st.warning(f"⚠️ DATA DUPLIKAT: '{barcode}' sudah ada!")
            else:
                try:
                    next_row = len(sheet_recap.col_values(2)) + 1
                    if next_row <= 1340:
                        sheet_recap.update_acell(f'B{next_row}', barcode)
                        sheet_recap.update_acell(f'C{next_row}', ts)
                        
                        # Update Sheet Harian
                        try:
                            ws_daily = sh.worksheet(sheet_daily_name)
                        except gspread.WorksheetNotFound:
                            ws_daily = sh.add_worksheet(title=sheet_daily_name, rows="1000", cols="5")
                            ws_daily.append_row(["Data Barcode", "Timestamp"])
                        
                        ws_daily.append_row([barcode, ts])
                        
                        st.toast(f"BERHASIL: {barcode}", icon="✅")
                        st.success(f"✅ Berhasil menyimpan {barcode}")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Sheet Penuh!")
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- MONITOR MONITOR TABEL (A, B, C) ---
    st.divider()
    st.subheader("📊 TABLE")

    raw_data = sheet_recap.get_all_values()
    if len(raw_data) > 0:
        header = raw_data[0][:3]
        # Pastikan header terisi
        header = [h if h else f"Col_{i+1}" for i, h in enumerate(header)]
        
        data_rows = [r[:3] for r in raw_data[1:] if len(r) >= 2]
        df = pd.DataFrame(data_rows, columns=header)
        df.insert(0, "Pilih", False)

        edited_df = st.data_editor(
            df.tail(15), 
            column_config={"Pilih": st.column_config.CheckboxColumn(required=True)},
            disabled=[c for c in df.columns if c != "Pilih"],
            hide_index=True,
            use_container_width=True,
            key="monitor_data"
        )

        if st.button("🗑️ HAPUS BARIS TERPILIH"):
            selected = edited_df[edited_df["Pilih"] == True].index.tolist()
            if selected:
                total_data = len(df)
                for idx in sorted(selected, reverse=True):
                    offset = max(0, total_data - 15)
                    row_to_del = idx + offset + 2
                    sheet_recap.delete_rows(row_to_del)
                
                st.toast("Terhapus!", icon="🗑️")
                st.rerun()
    else:
        st.info("Belum ada data.")
else:
    st.error("Gagal koneksi. Cek Cloud Secrets!")

st.caption(f"Mode Aktif: {theme_choice} | Cinnamoroll Recap v3.0")
