from __future__ import annotations
import io, json
from typing import Optional, List, Dict
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CSV_MIME  = "text/csv"

@st.cache_resource
def drive_client():
    info = st.secrets.get("google_service_account")
    if info is None and "google_service_account_json" in st.secrets:
        info = json.loads(st.secrets["google_service_account_json"])
    if info is None:
        raise RuntimeError("Missing service account credentials in secrets.")
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)

def list_files_in_folder(drive, folder_id: str, mime: Optional[str] = None) -> List[Dict]:
    q = [f"'{folder_id}' in parents", "trashed=false"]
    if mime: q.append(f"mimeType='{mime}'")
    res = drive.files().list(q=" and ".join(q), pageSize=1000,
                             fields="files(id,name,mimeType,modifiedTime,size)").execute()
    return res.get("files", [])

def upload_bytes(drive, folder_id: str, *, data: bytes, filename: str, mime_type: str) -> str:
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=False)
    file = drive.files().create(body={"name": filename,"parents":[folder_id]},
                                media_body=media, fields="id").execute()
    return file["id"]

def download_bytes(drive, file_id: str) -> bytes:
    req = drive.files().get_media(fileId=file_id)
    buf = io.BytesIO(); dl = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    return buf.getvalue()

def _find_steamfield_sheet(xls: pd.ExcelFile) -> str:
    names = xls.sheet_names
    norm = [s.strip().lower() for s in names]
    for cand in ("steamfield","steam field","steam_field"):
        if cand in norm: return names[norm.index(cand)]
    return names[0]

def process_xlsx_to_csv_bytes(raw_xlsx: bytes) -> bytes:
    xls = pd.ExcelFile(io.BytesIO(raw_xlsx))
    sheet = _find_steamfield_sheet(xls)
    try:
        df = pd.read_excel(xls, sheet_name=sheet, header=[0,1], skiprows=[0])
    except Exception:
        try:
            df = pd.read_excel(xls, sheet_name=sheet, header=[0,1])
        except Exception:
            df = pd.read_excel(xls, sheet_name=sheet, header=0)
    out = io.StringIO(); df.to_csv(out, index=False)
    return out.getvalue().encode("utf-8")

def convert_all_xlsx_in_folder_to_csv(drive, src_folder_id: str, dst_folder_id: str) -> list[dict]:
    xlsx_files = list_files_in_folder(drive, src_folder_id, mime=XLSX_MIME)
    existing = {f["name"] for f in list_files_in_folder(drive, dst_folder_id, mime=CSV_MIME)}
    rep = []
    for f in xlsx_files:
        base = f["name"].rsplit(".",1)[0]
        csv_name = f"{base}_Steamfield.csv"
        if csv_name in existing:
            rep.append({"file": f["name"], "status": "skipped (exists)"}); continue
        try:
            raw = download_bytes(drive, f["id"])
            csv_bytes = process_xlsx_to_csv_bytes(raw)
            upload_bytes(drive, dst_folder_id, data=csv_bytes, filename=csv_name, mime_type=CSV_MIME)
            rep.append({"file": f["name"], "status": "created", "csv": csv_name})
        except Exception as e:
            rep.append({"file": f["name"], "status": "error", "detail": str(e)})
    return rep

def load_csv_from_drive(drive, file_id: str) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(download_bytes(drive, file_id)))
