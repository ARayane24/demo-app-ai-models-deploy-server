import json
from gee_utils.drive_managment import export_image_to_drive, fetch_from_drive
from gee_utils.image_managment import fetch_sentinel2_image, generate_filename, get_roi
from utils_methods.model_management import ModelClient
from flask import Flask, request, send_file, render_template, jsonify
import ee
import tempfile
import os
import json
from datetime import datetime
import requests
import geemap


        

# Initialize Earth Engine
ee.Initialize(project=os.getenv('GEE_PROJECT'))
        
app = Flask(__name__)
S2_BANDS_TO_READ_FROM_TIFF_1_BASED = [1, 2, 3, 4, 5, 6]
MODEL_INPUT_IMG_SIZE = 256
MODEL_INPUT_NUM_BANDS = 6
CLASS_NAMES = ["non_cereal", "cereal"]

# Overlay settings - Highlighting "cereal" (class 1) in RED
HIGHLIGHT_CLASS_VALUE = 1 # 0 for "non_cereal", 1 for "cereal"
HIGHLIGHT_CLASS_NAME = CLASS_NAMES[HIGHLIGHT_CLASS_VALUE] # This will be "cereal"

FASTAPI_URL_UPLOAD = "http://localhost:8000/upload_model"

@app.route('/', methods=['GET'])
def index():
    return render_template("main.html")


# Make sure Earth Engine is initialized
ee.Initialize()

@app.route("/export_tif", methods=["POST"])
def export_tif():
    try:
        data = request.json
        coords, year = data["coords"], data["year"]
        print(f"Fetching Sentinel-2 image for year {year} and coords: {coords}")

        # Step 1: get ROI
        roi = get_roi( coords)
        print("ROI fetched successfully.")

        # Step 2: fetch Sentinel-2 image
        image = fetch_sentinel2_image( roi, year)
        print("Sentinel-2 image fetched successfully.")

        # Step 3: generate filename
        filename = generate_filename()
        print(f"Filename generated: {filename}")

        # Step 4: export image to Google Drive
        print(f"Exporting {filename} to Google Drive...")
        export_image_to_drive(ee, image, roi, filename)
        print(f"Exported {filename} to Google Drive.")

        return jsonify({"status": "success", "filename": filename})

    except Exception as e:
        # Print full exception info
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/download_tif_from_drive", methods=["POST"])
def download_tif_from_drive():
    try:
        data = request.json
        public_link = data["public_link"]
        filename = data["filename"]

        print(f"Downloading {filename} from Google Drive...")

        # Download from Drive
        filepath = fetch_from_drive(public_link,filename)

        if not filepath:
            raise Exception("Failed to download file from Google Drive.")

        print(f"Downloaded {filename} to {filepath}.")
        
        return send_file(filepath, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500   
    
@app.route("/flask_upload_model", methods=["POST"])
def flask_upload_model():
    """
    Receive model file + metadata from frontend and forward to FastAPI backend.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    model_file = request.files["file"]
    metadata_json = request.form.get("metadata")
    if not metadata_json:
        return jsonify({"error": "No metadata provided"}), 400

    # Prepare multipart/form-data for FastAPI
    files = {"model_file": (model_file.filename, model_file.stream, model_file.mimetype)}
    data = {"metadata_json": metadata_json}

    try:
        resp = requests.post(FASTAPI_URL_UPLOAD, files=files, data=data)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
import tempfile
import numpy as np
import requests
import rasterio
from PIL import Image
import io
import base64
import numpy as np
import requests
import torch
import torch.nn.functional as F
from PIL import Image

MODEL_INPUT_NUM_BANDS = 6
MODEL_INPUT_IMG_SIZE = 256
CLASS_NAMES = ["non_cereal", "cereal"]
HIGHLIGHT_CLASS_VALUE = 1
HIGHLIGHT_CLASS_NAME = CLASS_NAMES[HIGHLIGHT_CLASS_VALUE]
OVERLAY_COLOR = (255, 0, 0)
OVERLAY_ALPHA = 128
RGB_VISUALIZATION_BAND_INDICES_0_BASED = [2, 1, 0]
S2_BANDS_TO_READ_FROM_TIFF_1_BASED = [1, 2, 3, 4, 5, 6]
REMOTE_MODEL_ENDPOINT = "http://localhost:8000/predict"

# --- Preprocessing ---
def preprocess_uploaded_tif(file_storage):
    with rasterio.open(io.BytesIO(file_storage.read())) as src:
        print(f"📂 Opened TIFF with shape: {src.count} bands, {src.height}x{src.width}, dtype: {src.dtypes[0]}")
        selected_6bands_data = src.read(S2_BANDS_TO_READ_FROM_TIFF_1_BASED).astype(np.float32)
        print(f"✅ Read bands with shape: {selected_6bands_data.shape}")

        img_tensor = torch.from_numpy(selected_6bands_data).unsqueeze(0)
        resized_tensor = F.interpolate(img_tensor, size=(MODEL_INPUT_IMG_SIZE, MODEL_INPUT_IMG_SIZE), mode='bilinear', align_corners=False)
        model_input_numpy_single = resized_tensor.squeeze(0).numpy()
        print(f"📏 Resized input shape for model: {model_input_numpy_single.shape}")
        return np.expand_dims(model_input_numpy_single, axis=0), model_input_numpy_single

# --- Postprocessing ---
def postprocess_output(onnx_output_logits_batch):
    logits = np.array(onnx_output_logits_batch)
    print(f"📊 Received logits shape: {logits.shape}")
    
    if logits.ndim == 4 and logits.shape[0] == 1:
        logits = logits.squeeze(0)  # (2, 256, 256)
    
    pred_mask = np.argmax(logits, axis=0)  # (256, 256)
    print(f"🎯 Predicted mask shape: {pred_mask.shape}")
    return pred_mask.astype(np.uint8)

# --- RGB Display ---
def create_rgb_display(image_patch_6bands_resized, band_indices_rgb_0_based):
    rgb_bands = image_patch_6bands_resized[band_indices_rgb_0_based, :, :]
    stretched_bands = []
    for band in rgb_bands:
        p2, p98 = np.percentile(band, (2, 98))
        stretched = np.clip((band - p2) / (p98 - p2 + 1e-8), 0, 1)
        stretched_bands.append((stretched * 255).astype(np.uint8))
    rgb_array = np.stack(stretched_bands, axis=-1)
    return Image.fromarray(rgb_array)

# --- Overlay ---
def create_overlay(rgb_image, mask):
    original_rgba = rgb_image.convert("RGBA")
    overlay_img = Image.new("RGBA", rgb_image.size, (0, 0, 0, 0))
    highlight_color_layer = Image.new("RGBA", rgb_image.size, OVERLAY_COLOR + (OVERLAY_ALPHA,))
    pil_mask = Image.fromarray((mask == HIGHLIGHT_CLASS_VALUE).astype(np.uint8) * 255, mode="L")
    overlay_img.paste(highlight_color_layer, (0, 0), mask=pil_mask)
    return Image.alpha_composite(original_rgba, overlay_img).convert("RGB")




@app.route("/predict_and_show", methods=["POST"])
def predict_and_show():
    if 'file' not in request.files:
        return jsonify({"error": "No GeoTIFF file uploaded."}), 400

    if 'model_name' not in request.form:
        return jsonify({"error": "No model_name provided."}), 400

    REMOTE_MODEL_NAME = request.form["model_name"]

    try:
        # Preprocess input
        model_input, display_input = preprocess_uploaded_tif(request.files['file'])
        payload = {
            "model_name": REMOTE_MODEL_NAME,
            "inputs": model_input.tolist(),
            "params": {
                "device": "cpu"
            },
            "save_result": False
        }

        print("📤 Sending request to remote model...")
        response = requests.post(REMOTE_MODEL_ENDPOINT, json=payload)
        if response.status_code != 200:
            raise RuntimeError(f"Remote model error: {response.text}")

        print("✅ Received prediction from remote model.")
        prediction = np.array(response.json()["result"])

        # Postprocess output into overlay image
        mask = postprocess_output(prediction)
        rgb_image = create_rgb_display(display_input, RGB_VISUALIZATION_BAND_INDICES_0_BASED)
        overlay_image = create_overlay(rgb_image, mask)

        # Save overlay as PNG in-memory
        buf = io.BytesIO()
        overlay_image.save(buf, format='PNG')
        buf.seek(0)

        return send_file(
            buf,
            mimetype='image/png',
            download_name='overlay.png'
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    print(f"Starting Flask app. Access at http://0.0.0.0:5001 or http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)