var coords = { lat: 36.81897, lng: 10.16579 };

var osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 });
var toner = L.tileLayer('https://stamen-tiles.a.ssl.fastly.net/toner/{z}/{x}/{y}.png', { maxZoom: 20 });

var map = L.map('map', { center: [coords.lat, coords.lng], zoom: 13, layers: [osm] });

var marker = L.marker([coords.lat, coords.lng]).bindPopup("Hello from Flask!").openPopup();

var drawnItems = new L.FeatureGroup();
map.addLayer(drawnItems);

var drawControl = new L.Control.Draw({
  edit: { featureGroup: drawnItems },
  draw: { polygon: true, rectangle: true, circle: false, marker: false, polyline: false }
});
map.addControl(drawControl);

var currentGeoJSON = null;
let tifLayer = null; // store current TIF layer
let overlayMaps = { "Marker": marker, "Drawn Shapes": drawnItems }; // initial overlays
let tifCount = 0; // for unique layer names

// Initialize Layer Control
var layerControl = L.control.layers(
  { "OpenStreetMap": osm, "Stamen Toner": toner },
  overlayMaps
).addTo(map);

map.on(L.Draw.Event.CREATED, function (e) {
  var layer = e.layer;
  drawnItems.addLayer(layer);
  currentGeoJSON = layer.toGeoJSON();
  console.log("Drawn shape:", currentGeoJSON);
  document.getElementById("downloadBtn").style.display = "inline-block";
});

document.getElementById("downloadBtn").addEventListener("click", function() {
   if (!currentGeoJSON) { alert("Draw a shape first!"); return; }
  console.log("Sending:", currentGeoJSON.geometry.coordinates[0]);
  var year = prompt("Enter the year for the Sentinel-2 image (e.g., 2020):", "2020");

  // Trigger export request
  fetch("/export_tif", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ coords: currentGeoJSON.geometry.coordinates[0], year: year })
  })
  .then(response => response.json())
  .then(data => {
      if (data.status === "success") {
          let link = prompt("File exported to Drive! Enter the public share link to download:");
          if (link) {
              let filename = prompt("File name (with .tif extension):", "image.tif");
              if (!filename || filename.trim() === "") filename = "image.tif";
              fetch("/download_tif_from_drive", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ public_link: link, filename: filename})
              })
              .then(resp => resp.blob())
              .then(blob => {
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = filename;
                  document.body.appendChild(a);
                  a.click();
                  a.remove();
              });
          }
      } else {
          alert("Export failed: " + data.error);
      }
  })
  .catch(err => alert("Error: " + err));
});

// Draw TIF button triggers file picker
document.getElementById("drawBtn").addEventListener("click", function() {
    document.getElementById("tifInput").click();
});

// When TIF selected
document.getElementById("tifInput").addEventListener("change", async function(event) {
    const file = event.target.files[0];
    if (!file) return;

    const arrayBuffer = await file.arrayBuffer();
    const georaster = await parseGeoraster(arrayBuffer);

    // Remove previous layer if exists
    if (tifLayer) {
        map.removeLayer(tifLayer);
        // Remove old TIF from layer control
        Object.keys(overlayMaps).forEach(name => {
            if (overlayMaps[name] === tifLayer) delete overlayMaps[name];
        });
    }

    tifLayer = new GeoRasterLayer({
        georaster: georaster,
        opacity: 0.7,
        resolution: 256
    }).addTo(map);

    map.fitBounds(tifLayer.getBounds());

    // Add to overlay maps & layer control
    const layerName = `TIF Layer ${++tifCount}: ${file.name}`;
    overlayMaps[layerName] = tifLayer;
    layerControl.addOverlay(tifLayer, layerName);

    console.log("TIF layer added to map:", file.name);
});

// Send button
document.getElementById("sendBtn").addEventListener("click", function() {
    const tifInput = document.getElementById("tifInput");
    tifInput.click();

    tifInput.onchange = async function(event) {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append("file", file);
        var model_name = prompt("Enter the model name (e.g., xx.onnx):");
        formData.append("model_name", model_name); // <-- pass the model name

        try {
            const resp = await fetch("/predict_and_show", {
                method: "POST",
                body: formData // DO NOT set Content-Type manually
            });

            if (!resp.ok) throw new Error("Prediction failed");

            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);

            // Add new overlay layer
            const predictionLayer = L.imageOverlay(url, tifLayer.getBounds(), { opacity: 0.6 }).addTo(map);

            // Add to layer control
            if (!window.layerControl) {
                window.layerControl = L.control.layers({}, { "Prediction Overlay": predictionLayer }).addTo(map);
            } else {
                window.layerControl.addOverlay(predictionLayer, "Prediction Overlay");
            }

            alert("Prediction overlay added!");
        } catch (err) {
            console.error(err);
            alert("Prediction failed: " + err);
        } finally {
            tifInput.value = "";
        }
    };
});





// Upload AI Model
document.getElementById("uploadModelBtn").addEventListener("click", function() {
  document.getElementById("modelFile").click();
});

document.getElementById("modelFile").addEventListener("change", function(event) {
  var file = event.target.files[0];
  if (!file) return;
  var formData = new FormData();
  formData.append("file", file);
  var metadata = {
    name: "MOE System Final",
    description: "Multi-Output Encoder system in ONNX format.",
    tags: ["segmentation", "remote sensing", "onnx"],
    framework: "onnx"
  };
  formData.append("metadata", JSON.stringify(metadata));

  // Send to Flask endpoint
  fetch("/flask_upload_model", {
    method: "POST",
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    console.log("✅ Upload response:", data);
    alert("Model uploaded successfully!");
  })
  .catch(err => {
    console.error("❌ Upload failed:", err);
    alert("Model upload failed!");
  });
});
