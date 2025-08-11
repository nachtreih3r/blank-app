import streamlit as st
from pathlib import Path
import pandas as pd
from src.stage1 import make_csvs_from_excels
from src.stage2 import build_master_dataset

st.set_page_config(page_title="Thunderbolt ⚡ — Stage 1 & 2", layout="wide")
st.title("Project Thunderbolt — Stage 1 & 2")

# workspace folders (persist in the repo)
WORKDIR = Path("./workspace")
EXCEL_DIR = WORKDIR / "excels"
CSV_DIR   = WORKDIR / "steamfield_csvs"
for p in (EXCEL_DIR, CSV_DIR):
    p.mkdir(parents=True, exist_ok=True)

tab1, tab2 = st.tabs(["Stage 1: Excel → CSV", "Stage 2: Merge & Clean"])

with tab1:
    st.subheader("Upload Daily Generation Report Excel files")
    uploads = st.file_uploader(
        "Upload .xlsx (pattern: 'Daily Generation Report_*.xlsx')",
        type=["xlsx"], accept_multiple_files=True
    )
    col_a, col_b = st.columns([1,1])
    with col_a:
        if uploads and st.button("Save uploads"):
            for uf in uploads:
                (EXCEL_DIR / uf.name).write_bytes(uf.read())
            st.success(f"Saved {len(uploads)} file(s) to {EXCEL_DIR}")

    with col_b:
        if st.button("Run Stage 1 (make CSVs)"):
            new_csvs = make_csvs_from_excels(EXCEL_DIR, CSV_DIR)
            st.success(f"Stage 1 done. New CSVs: {len(new_csvs)}")
            if new_csvs:
                st.write([p.name for p in new_csvs])

    st.caption(f"Excel dir: {EXCEL_DIR.resolve()}")
    st.caption(f"CSV dir: {CSV_DIR.resolve()}")

with tab2:
    st.subheader("Build Master Dataset")
    fmt = st.selectbox("Timestamp display format",
                       ["%d-%m-%Y %H%MH", "%d-%m-%Y %H:%M", "%Y-%m-%d %H:%M"],
                       index=0)
    if st.button("Run Stage 2 (merge & clean)"):
        master = build_master_dataset(CSV_DIR, timestamp_format=fmt)
        if master.empty:
            st.warning("No valid Steamfield CSVs found. Run Stage 1 first.")
        else:
            st.success(f"Master dataset ready. Rows: {len(master)}  |  Cols: {len(master.columns)}")
            st.dataframe(master.head(50))
            st.download_button(
                "Download master.csv",
                master.to_csv(index=False),
                "master.csv",
                "text/csv"
            )