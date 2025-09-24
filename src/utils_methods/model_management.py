import os
import json
import requests


class ModelClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    # === Upload model ===
    def upload_model(self, model_path: str, metadata: dict):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"❌ File not found: {model_path}")

        with open(model_path, "rb") as f:
            files = {"model_file": (os.path.basename(model_path), f, "application/octet-stream")}
            data = {"metadata_json": json.dumps(metadata)}

            response = requests.post(f"{self.base_url}/upload_model", files=files, data=data)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Upload failed ({response.status_code}): {response.text}")

    # === List all models ===
    def list_models(self):
        response = requests.get(f"{self.base_url}/models")
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"List failed ({response.status_code}): {response.text}")

    # === Delete model ===
    def delete_model(self, model_id: str):
        response = requests.delete(f"{self.base_url}/models/{model_id}")
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Delete failed ({response.status_code}): {response.text}")

    # === Run inference ===
    def run_inference(self, model_id: str, input_data: dict):
        response = requests.post(f"{self.base_url}/predict/{model_id}", json=input_data)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Inference failed ({response.status_code}): {response.text}")

