import streamlit as st
import pandas as pd
from src.drive_utils import (
    drive_client, list_files_in_folder, upload_bytes,
    convert_all_xlsx_in_folder_to_csv, load_csv_from_drive,
    XLSX_MIME, CSV_MIME
)

st.set_page_config(page_title="Thunderbolt ⚡ — GDrive Pipeline", layout="wide")
st.title("Project Thunderbolt — Google Drive Data Pipeline")

RAW_XLSX_FOLDER_ID = st.secrets.get("RAW_XLSX_FOLDER_ID", "")
CSV_FOLDER_ID      = st.secrets.get("CSV_FOLDER_ID", "")

with st.sidebar:
    st.subheader("Google Drive Folders")
    RAW_XLSX_FOLDER_ID = st.text_input("RAW_XLSX_FOLDER_ID", value=RAW_XLSX_FOLDER_ID)
    CSV_FOLDER_ID      = st.text_input("CSV_FOLDER_ID", value=CSV_FOLDER_ID)

try:
    drv = drive_client()
    st.sidebar.success("Drive auth OK")
except Exception as e:
    drv = None
    st.sidebar.error(f"Drive auth error: {e}")

tab_up, tab_conv, tab_csv, tab_an = st.tabs([
    "1) Upload XLSX → Drive", "2) Convert RAW → CSV", "3) Browse CSVs", "4) Analyze CSVs"
])

with tab_up:
    st.subheader("Upload .xlsx to RAW folder in Drive")
    files = st.file_uploader("XLSX only", type=["xlsx"], accept_multiple_files=True)
    if st.button("Upload to Drive"):
        if not drv or not RAW_XLSX_FOLDER_ID:
            st.error("Missing Drive auth or RAW folder ID")
        else:
            n = 0
            for f in files or []:
                upload_bytes(drv, RAW_XLSX_FOLDER_ID, data=f.read(), filename=f.name, mime_type=XLSX_MIME)
                n += 1
            st.success(f"Uploaded {n} file(s) to RAW")

    if drv and RAW_XLSX_FOLDER_ID:
        st.caption("RAW contents:")
        st.dataframe(pd.DataFrame(list_files_in_folder(drv, RAW_XLSX_FOLDER_ID, XLSX_MIME)))

with tab_conv:
    st.subheader("Convert all RAW XLSX → CSV (stored in CSV folder)")
    if st.button("Run conversion"):
        if not drv or not (RAW_XLSX_FOLDER_ID and CSV_FOLDER_ID):
            st.error("Missing Drive auth or folder IDs")
        else:
            rep = convert_all_xlsx_in_folder_to_csv(drv, RAW_XLSX_FOLDER_ID, CSV_FOLDER_ID)
            st.success("Done")
            st.dataframe(pd.DataFrame(rep))

with tab_csv:
    st.subheader("CSV files in Drive")
    if drv and CSV_FOLDER_ID:
        st.dataframe(pd.DataFrame(list_files_in_folder(drv, CSV_FOLDER_ID, CSV_MIME)))
    else:
        st.info("Enter CSV folder ID to list files")

with tab_an:
    st.subheader("Load a CSV from Drive for analysis")
    if drv and CSV_FOLDER_ID:
        items = list_files_in_folder(drv, CSV_FOLDER_ID, CSV_MIME)
        options = {f["name"]: f["id"] for f in items}
        pick = st.selectbox("Choose CSV", list(options.keys()))
        if pick and st.button("Load selected"):
            df = load_csv_from_drive(drv, options[pick])
            st.write(df.head(50))
            st.download_button("Download CSV", df.to_csv(index=False), file_name=pick, mime="text/csv")
    else:
        st.info("Enter CSV folder ID to continue")