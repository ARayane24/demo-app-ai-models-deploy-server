import ee
from datetime import datetime

def get_roi(coords):
    """Convert coordinates to Earth Engine Polygon ROI"""
    return ee.Geometry.Polygon(coords)

def fetch_sentinel2_image(roi, year=2024):
    """Fetch lowest-cloud Sentinel-2 image for given ROI and year"""
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterDate(f"{year}-01-01", f"{year}-12-31")
        .filterBounds(roi)
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )

    image = collection.first()
    if not image:
        raise ValueError("No Sentinel-2 image found for given ROI/date")
    return image

def generate_filename(prefix="sentinel2", ext="tif"):
    """Generate timestamped filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{ext}"
