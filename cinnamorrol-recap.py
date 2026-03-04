import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Cinnamoroll Wahana Recap", page_icon="☁️", layout="wide")

# --- CUSTOM CSS: GLOSSY CINNAMOROLL BLUE ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #e0f2fe 0%, #ffffff 50%, #bae6fd 100%);
    }

    .main-title {
        color: #000000;
        font-family: 'Segoe UI', Tahoma, Geneva, sans-serif;
        font-weight: 800;
        text-align: center;
        font-size: 2.5rem;
        margin-bottom: 10px;
    }

    /* Card Glossy Style */
    div[data-testid="stForm"], .glossy-container {
        background: rgba(255, 255, 255, 0.4);
        backdrop-filter: blur(12px) saturate(170%);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.6);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.05);
        padding: 20px;
    }

    /* Blue Glossy Button */
    .stButton>button {
        background: linear-gradient(90deg, #7dd3fc 0%, #0ea5e9 100%);
        color: white;
        border-radius: 12px;
        border: none;
        font-weight: bold;
        transition: 0.3s ease;
        height: 3em;
    }

    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 15px rgba(14, 165, 233, 0.4);
        color: white;
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
    
    st.markdown("<h1 class='main-title'>☁️ CINNAMOROLL RECAP SYSTEM</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#5fb0e8;'>Silakan scan barcode barang wahana kamu ✨</p>", unsafe_allow_html=True)

    # --- BAGIAN INPUT ---
    with st.form("input_section", clear_on_submit=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            date_pick = st.date_input("📅 Pilih Tanggal Rekap", datetime.now())
        with c2:
            barcode = st.text_input("📥 Sandbox Input (Fokuskan Cursor di Sini)", placeholder="Scan Honeywell...")
        
        btn_submit = st.form_submit_button("SIMPAN DATA ✨")

    if btn_submit:
        if not barcode:
            st.error("❌ Scan Gagal: Tidak ada data yang terdeteksi!")
            st.toast("Gagal! Input kosong.", icon="❌")
        else:
            current_ts = datetime.now().strftime("%H:%M:%S")
            sheet_daily_name = date_pick.strftime("%d_%m_%Y_Rekap Wahana")

            # --- LOGIKA CEK DUPLIKAT (Kolom B) ---
            # Ambil data Kolom B baris 2 sampai 1340
            all_data_b = sheet_recap.col_values(2)[1:1340] 
            
            if barcode in all_data_b:
                st.warning(f"⚠️ Scan Duplikat: Data '{barcode}' sudah pernah diinput sebelumnya!")
                st.toast(f"Duplikat deteksi: {barcode}", icon="⚠️")
            else:
                try:
                    # 1. Update Report Recap (A=Kosong/No, B=Data, C=Timestamp)
                    next_idx = len(sheet_recap.col_values(2)) + 1
                    if next_idx <= 1340:
                        sheet_recap.update_acell(f'B{next_idx}', barcode)
                        sheet_recap.update_acell(f'C{next_idx}', current_ts)
                        
                        # 2. Update Sheet Harian (Buat jika belum ada)
                        try:
                            ws_daily = sh.worksheet(sheet_daily_name)
                        except gspread.WorksheetNotFound:
                            ws_daily = sh.add_worksheet(title=sheet_daily_name, rows="1000", cols="5")
                            ws_daily.append_row(["Data Barcode", "Timestamp"])
                        
                        ws_daily.append_row([barcode, current_ts])
                        
                        # --- NOTIFIKASI BERHASIL ---
                        st.success(f"✅ Scan Berhasil: '{barcode}' telah tersimpan di Cloud!")
                        st.toast(f"Berhasil simpan: {barcode}", icon="✨")
                        time.sleep(1) # Memberi jeda agar user bisa melihat notifikasi
                        st.rerun()
                    else:
                        st.error("❌ Gagal: Kapasitas Sheet Report Recap Penuh (Maks 1340 Baris)!")
                except Exception as e:
                    st.error(f"❌ Terjadi Kesalahan: {e}")

    # --- MONITOR TABEL (KOLOM A, B, C) ---
    st.markdown("---")
    st.subheader("📊 Live Monitor (Kolom A, B, C)")

    raw_rows = sheet_recap.get_all_values()
    
    if len(raw_rows) > 0:
        header = raw_rows[0][:3] 
        # Pastikan kolom A, B, C memiliki judul di GSheet
        if not header[0]: header[0] = "No"
        if not header[1]: header[1] = "Data Barcode"
        if not header[2]: header[2] = "Timestamp"
            
        data_body = [r[:3] for r in raw_rows[1:] if len(r) >= 2]
        df = pd.DataFrame(data_body, columns=header)
        df.insert(0, "Pilih", False)

        edited_df = st.data_editor(
            df.tail(15), 
            column_config={"Pilih": st.column_config.CheckboxColumn(required=True)},
            disabled=[c for c in df.columns if c != "Pilih"],
            hide_index=True,
            use_container_width=True,
            key="monitor_table"
        )

        if st.button("🗑️ Hapus Baris Terpilih"):
            selected_rows = edited_df[edited_df["Pilih"] == True].index.tolist()
            if selected_rows:
                total_rows = len(df)
                for idx in sorted(selected_rows, reverse=True):
                    offset = max(0, total_rows - 15)
                    gsheet_row_to_del = idx + offset + 2
                    sheet_recap.delete_rows(gsheet_row_to_del)
                
                st.toast("Data berhasil dihapus!", icon="🗑️")
                st.rerun()
            else:
                st.info("Ceklist data pada tabel untuk menghapus.")
    else:
        st.info("Menunggu data masuk dari scanner...")

else:
    st.error("Gagal Menghubungkan ke Cloud. Pastikan 'gcp_service_account' di Secrets sudah benar!")

st.caption("Cinnamoroll Wahana System © 2024 - Elegant Glossy Edition")
