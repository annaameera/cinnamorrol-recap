import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Wahana Recap", page_icon="☁️")

# --- CSS LITE (Tanpa Efek Berat) ---
st.markdown("""
    <style>
    /* Warna solid biru muda agar ringan di render */
    .stApp { background-color: #F0F9FF; }
    
    /* Judul Hitam Tetap Tegas */
    .lite-title {
        color: #000000;
        font-family: sans-serif;
        font-weight: bold;
        text-align: center;
        margin-bottom: 5px;
    }
    
    /* Tombol Biru Solid (Tanpa Gradasi/Bayangan Berat) */
    .stButton>button {
        background-color: #38BDF8;
        color: white;
        border-radius: 8px;
        border: none;
        width: 100%;
        height: 3em;
    }
    
    /* Input Box Sederhana */
    .stTextInput>div>div>input {
        border: 2px solid #BAE6FD;
        border-radius: 8px;
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
    st.markdown("<h2 class='lite-title'>☁️ RECAP WAHANA</h2>", unsafe_allow_html=True)

    # --- SIDEBAR RINGAN ---
    with st.sidebar:
        selected_date = st.date_input("Pilih Tanggal", datetime.now())
        st.info("Mode: Lite (Mobile Optimized)")

    # --- INPUT FORM ---
    with st.form("lite_input", clear_on_submit=True):
        barcode = st.text_input("Input Barcode:", placeholder="Scan...")
        btn_submit = st.form_submit_button("SIMPAN DATA")

    if btn_submit and barcode:
        ts = datetime.now().strftime("%H:%M:%S")
        sheet_daily_name = selected_date.strftime("%d_%m_%Y_Rekap Wahana")

        # Cek Duplikat (Hanya ambil kolom B agar hemat data)
        b_values = sheet_recap.col_values(2)[1:1340]
        
        if barcode in b_values:
            st.toast(f"DUPLIKAT: {barcode}", icon="⚠️")
        else:
            try:
                # Update Report Recap
                next_r = len(b_values) + 2 # +2 karena index gsheet dan header
                if next_r <= 1340:
                    sheet_recap.update_acell(f'B{next_r}', barcode)
                    sheet_recap.update_acell(f'C{next_r}', ts)
                    
                    # Update/Buat Sheet Harian
                    try:
                        ws_daily = sh.worksheet(sheet_daily_name)
                    except:
                        ws_daily = sh.add_worksheet(title=sheet_daily_name, rows="1000", cols="5")
                        ws_daily.append_row(["Data", "Time"])
                    
                    ws_daily.append_row([barcode, ts])
                    st.toast("✅ Berhasil!", icon="✨")
                    st.rerun()
            except Exception as e:
                st.error("Error Simpan")

    # --- TABEL MONITOR (Hanya A, B, C) ---
    st.markdown("---")
    try:
        # Hanya ambil 20 baris terakhir secara langsung dari GSheet untuk hemat RAM hp
        raw_data = sheet_recap.get_all_values()
        if len(raw_data) > 1:
            header = raw_data[0][:3]
            # Ambil hanya 10 baris terakhir agar tabel tidak 'berat' saat di-scroll di hp
            rows = [r[:3] for r in raw_data[-10:]] 
            
            df = pd.DataFrame(rows, columns=header)
            df.insert(0, "Hapus", False)

            # Editor tabel dengan fitur hapus
            edited_df = st.data_editor(
                df,
                column_config={"Hapus": st.column_config.CheckboxColumn()},
                disabled=header,
                hide_index=True,
                use_container_width=True,
                key="table_lite"
            )

            if st.button("Hapus Terpilih"):
                selected = edited_df[edited_df["Hapus"] == True].index.tolist()
                if selected:
                    total_data = len(raw_data)
                    for idx in sorted(selected, reverse=True):
                        # Hitung baris asli: total_data - (jumlah data ditampilkan - idx)
                        row_to_del = total_data - (len(rows) - idx - 1)
                        sheet_recap.delete_rows(int(row_to_del))
                    st.rerun()
    except:
        st.write("Gagal memuat tabel.")

else:
    st.error("Koneksi Error")
