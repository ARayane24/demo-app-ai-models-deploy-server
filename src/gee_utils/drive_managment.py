import os

import requests
from .config import DOWNLOAD_DIR
import logging
import time
import os
import re

def get_drive_file_id(url: str) -> str | None:
    """
    Extracts the Google Drive file ID from a public share link.

    Args:
        url (str): Google Drive shareable link.

    Returns:
        str | None: The extracted file ID, or None if not found.
    """
    # Pattern for "file/d/FILE_ID"
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    
    # Pattern for "id=FILE_ID"
    match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    
    return None

def export_image_to_drive(ee,image, roi, filename, scale=10, folder=os.getenv('GDRIVE_FOLDER')):
    """
    Export an Earth Engine image to Google Drive and wait for completion.
    """
    try:
        print(f"🚀 Starting export of {filename} to Google Drive folder '{folder}'...")

        task = ee.batch.Export.image.toDrive(
            image=image.toUint16(),
            description=filename,
            folder=folder,
            fileNamePrefix=filename,
            scale=scale,
            region=roi,
            maxPixels=1e13
        )
        task.start()

        logging.info(f"✅ Export task '{filename}' started successfully.")

        # Wait for task to complete
        while task.active():
            print("⏳ Exporting... still in progress...")
            time.sleep(30)  # check every 30 seconds

        status = task.status()
        if status['state'] == 'COMPLETED':
            print(f"🎉 Export '{filename}' completed successfully.")
        else:
            logging.error(f"❌ Export failed. Status: {status}")
        return task

    except Exception as e:
        logging.error(f"❌ Failed to export image '{filename}' to Drive: {e}")
        return None


def download_from_drive_file_id(file_id: str, filename: str, download_dir: str):
    """
    Download a Google Drive file (shared link) by file_id.

    Args:
        file_id (str): The Google Drive file ID.
        filename (str): Local filename to save as.
        download_dir (str): Directory to save the file.

    Returns:
        str: Path to the downloaded file, or None on failure.
    """
    try:
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(url, stream=True)

        if response.status_code != 200:
            logging.error(f"❌ Failed to fetch file {file_id}: HTTP {response.status_code}")
            return None

        os.makedirs(download_dir, exist_ok=True)
        filepath = os.path.join(download_dir, filename)

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(1024 * 1024):
                f.write(chunk)

        logging.info(f"📥 Downloaded '{filename}' to {filepath}")
        return filepath

    except Exception as e:
        logging.error(f"❌ Error downloading file from Drive: {e}")
        return None

def fetch_from_drive(public_link,filename):
    """Download exported file from Google Drive to local folder"""
    file_id_drive = get_drive_file_id(public_link)
    return download_from_drive_file_id(file_id_drive,filename, DOWNLOAD_DIR)
