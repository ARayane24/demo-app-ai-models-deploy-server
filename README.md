## Demo App: Using the Server with Google Earth Engine

This demo app shows how the server can be used to interact with Google Earth Engine (GEE).

### Steps to Authenticate and Set Project

1. **Authenticate to Google Earth Engine (GEE):**
    ```bash
    earthengine authenticate
    ```

2. **Set your GEE project:**
    ```bash
    earthengine set_project <PROJECT_ID>
    ```
    Replace `<PROJECT_ID>` with your actual Google Cloud project ID.

### Configure Environment Variables

Create a `.env` file in the project root with the following content:

```env
GEE_PROJECT=
GDRIVE_FOLDER=
```
Fill in your Google Earth Engine project ID and Google Drive folder name as needed.
