import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="WAHANA Recap", page_icon="☁️")

# --- CSS ULTRA LITE (Fokus Kecepatan & Kontras) ---
st.markdown("""
    <style>
    /* Background Biru Solid Sederhana */
    .stApp { background-color: #E0F2FE; }
    
    /* Judul & Sub-judul Hitam Pekat */
    .lite-title {
        color: #000000 !important;
        font-family: sans-serif;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0px;
        padding-top: 10px;
    }
    
    .lite-sub {
        color: #000000 !important;
        font-family: sans-serif;
        font-weight: 600;
        text-align: center;
        font-size: 0.9rem;
        margin-bottom: 20px;
    }

    h3 {
        color: #000000 !important;
        font-weight: bold !important;
    }
    
    /* Tombol Biru Standar (Ringan) */
    .stButton>button {
        background-color: #0EA5E9;
        color: white;
        border-radius: 5px;
        border: none;
        width: 100%;
        font-weight: bold;
    }
    
    /* Input Box Standar */
    .stTextInput>div>div>input {
        border: 1px solid #000000;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- KONEKSI GSHEET (DIOPTIMALKAN) ---
@st.cache_resource
def init_gsheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        url = "https://docs.google.com/spreadsheets/d/1vlwLdTxPLDnDkrn4luNKnRr_SH5TG-YJXK5NZAdWCVQ/edit?usp=sharing"
        return client.open_by_url(url)
    except Exception:
        return None

sh = init_gsheet()

if sh:
    sheet_recap = sh.worksheet("Report Recap")
    
    # Judul & Sub-judul Hitam
    st.markdown("<h1 class='lite-title'> WAHANA RECAP</h1>", unsafe_allow_html=True)
    st.markdown("<p class='lite-sub'>Mode Lite: Ringan & Cepat</p>", unsafe_allow_html=True)

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("<b style='color:black;'>PENGATURAN</b>", unsafe_allow_html=True)
        selected_date = st.date_input("Pilih Tanggal", datetime.now())

    # --- INPUT FORM ---
    with st.form("input_lite", clear_on_submit=True):
        barcode = st.text_input("Input Barcode / Manual:", placeholder="Scan...")
        btn_submit = st.form_submit_button("SIMPAN DATA ✨")

    if btn_submit and barcode:
        ts = datetime.now().strftime("%H:%M:%S")
        sheet_name = selected_date.strftime("%d_%m_%Y_Rekap Wahana")

        # Cek Duplikat (Hanya ambil kolom B agar hemat memori hp)
        try:
            b_values = sheet_recap.col_values(2)[1:1340]
            
            if barcode in b_values:
                st.toast(f"DUPLIKAT: {barcode}", icon="⚠️")
                st.warning(f"Data {barcode} sudah ada!")
            else:
                # Update Report Recap
                next_row = len(b_values) + 2
                if next_row <= 1340:
                    sheet_recap.update_acell(f'B{next_row}', barcode)
                    sheet_recap.update_acell(f'C{next_row}', ts)
                    
                    # Update Sheet Harian
                    try:
                        ws_daily = sh.worksheet(sheet_name)
                    except:
                        ws_daily = sh.add_worksheet(title=sheet_name, rows="1000", cols="5")
                        ws_daily.append_row(["Data", "Waktu"])
                    
                    ws_daily.append_row([barcode, ts])
                    st.toast("✅ Berhasil!", icon="✨")
                    st.rerun()
                else:
                    st.error("Batas Baris Penuh!")
        except Exception as e:
            st.error("Gagal Simpan!")

    # --- MONITOR TABEL (A, B, C) ---
    st.markdown("---")
    st.markdown("### 📊 TABLE")
    
    try:
        raw = sheet_recap.get_all_values()
        if len(raw) > 1:
            header = raw[0][:3] # No, Data, Timestamp
            # Hanya ambil 8 data terakhir agar scroll ponsel tidak macet
            recent_data = [r[:3] for r in raw[-8:]]
            
            df = pd.DataFrame(recent_data, columns=header)
            df.insert(0, "Hapus", False)

            edited = st.data_editor(
                df,
                column_config={"Hapus": st.column_config.CheckboxColumn()},
                disabled=header,
                hide_index=True,
                use_container_width=True,
                key="lite_table"
            )

            if st.button("Hapus Terpilih"):
                to_delete = edited[edited["Hapus"] == True].index.tolist()
                if to_delete:
                    total = len(raw)
                    for idx in sorted(to_delete, reverse=True):
                        # Rumus baris: Total - (Jumlah ditampil - idx - 1)
                        row_num = total - (len(recent_data) - idx - 1)
                        sheet_recap.delete_rows(int(row_num))
                    st.rerun()
        else:
            st.info("Data Kosong")
    except:
        st.write("Tabel tidak dapat dimuat.")

else:
    st.error("Koneksi Error. Cek Cloud Secrets.")

st.caption("v.Lite Mobile Optimized")
