import streamlit as st
import pandas as pd
from src.drive_utils import (
    drive_client, list_files_in_folder, upload_bytes,
    convert_all_xlsx_in_folder_to_csv, load_csv_from_drive,
    XLSX_MIME, CSV_MIME
)

st.set_page_config(page_title="Thunderbolt ⚡ — GDrive Pipeline", layout="wide")
st.title("Project Thunderbolt — Google Drive Data Pipeline")

# --- read once from Secrets (fail fast if missing) ---
def get_secret(name: str) -> str:
    try:
        return st.secrets[name]
    except Exception:
        st.error(f"Missing `{name}` in Secrets."); st.stop()

# read folder IDs from the drive_folders section
RAW_XLSX_FOLDER_ID = st.secrets["drive_folders"]["RAW_XLSX_FOLDER_ID"]
CSV_FOLDER_ID      = st.secrets["drive_folders"]["CSV_FOLDER_ID"]

# Sidebar: show which folders are in use (read-only)
with st.sidebar:
    st.subheader("Google Drive Folders (from Secrets)")
    st.code(f"RAW  = {RAW_XLSX_FOLDER_ID[:6]}…{RAW_XLSX_FOLDER_ID[-6:]}\nCSV  = {CSV_FOLDER_ID[:6]}…{CSV_FOLDER_ID[-6:]}")
    # Build the Drive client
    try:
        drv = drive_client()
        st.success("Drive auth OK")
    except Exception as e:
        st.error(f"Drive auth error: {e}")
        st.stop()

tab_up, tab_conv, tab_csv, tab_an = st.tabs([
    "1) Upload XLSX → Drive", "2) Convert RAW → CSV", "3) Browse CSVs", "4) Analyze CSVs"
])

# 1) Upload raw XLSX to Drive
with tab_up:
    st.subheader("Upload .xlsx to RAW folder in Drive")
    files = st.file_uploader("XLSX only", type=["xlsx"], accept_multiple_files=True)
    if st.button("Upload to Drive"):
        n = 0
        for f in files or []:
            upload_bytes(drv, RAW_XLSX_FOLDER_ID, data=f.read(), filename=f.name, mime_type=XLSX_MIME)
            n += 1
        st.success(f"Uploaded {n} file(s) to RAW")

    st.caption("RAW contents:")
    st.dataframe(pd.DataFrame(list_files_in_folder(drv, RAW_XLSX_FOLDER_ID, XLSX_MIME)))

# 2) Convert RAW → CSV (in Drive)
with tab_conv:
    st.subheader("Convert all RAW XLSX → CSV (stored in CSV folder)")
    if st.button("Run conversion"):
        rep = convert_all_xlsx_in_folder_to_csv(drv, RAW_XLSX_FOLDER_ID, CSV_FOLDER_ID)
        st.success("Conversion complete")
        st.dataframe(pd.DataFrame(rep))

# 3) Browse CSVs
with tab_csv:
    st.subheader("CSV files in Drive")
    st.dataframe(pd.DataFrame(list_files_in_folder(drv, CSV_FOLDER_ID, CSV_MIME)))

# 4) Analyze CSVs
with tab_an:
    st.subheader("Load a CSV from Drive for analysis")
    items = list_files_in_folder(drv, CSV_FOLDER_ID, CSV_MIME)
    options = {f["name"]: f["id"] for f in items}
    pick = st.selectbox("Choose CSV", list(options.keys()))
    if pick and st.button("Load selected"):
        df = load_csv_from_drive(drv, options[pick])
        st.write(df.head(50))
        st.download_button("Download CSV", df.to_csv(index=False), file_name=pick, mime="text/csv")