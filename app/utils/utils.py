from datetime import date, datetime
from typing import Any, Dict, List
from ..config import API_BASE_URL
from ..config import AZURE_STORAGE_ACCOUNT, AZURE_STORAGE_KEY

def to_iso_date(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    return str(value)

from typing import List, Dict
import os



from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta

def normalize_files(files: List[Dict]) -> List[Dict]:
    """
    Normalize medical records so they always return valid Azure Blob SAS URLs.
    """
    if not files:
        return []
    
    normalized = []
    for f in files:
        blob_path = f.get("filepath") or f.get("url")
        if not blob_path:
            continue

        filename = f.get("filename")

        # Handle both "container/blob" format and full URL format
        if str(blob_path).startswith("http"):
            # Extract container and blob name from full URL
            parts = blob_path.split(".blob.core.windows.net/")[-1]
            container, blob_name = parts.split("/", 1)
        else:
            container, blob_name = blob_path.split("/", 1)

        # Always generate SAS (since container is private)
        sas_token = generate_blob_sas(
            account_name=AZURE_STORAGE_ACCOUNT,
            container_name=container,
            blob_name=blob_name,
            account_key=AZURE_STORAGE_KEY,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)
        )

        file_url = f"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/{container}/{blob_name}?{sas_token}"

        normalized.append({
            "filename": filename,
            "url": file_url
        })

    return normalized

