import os

# Base directory
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Local download folder
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
