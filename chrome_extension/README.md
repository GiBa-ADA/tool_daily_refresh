# Chrome Extension: ADA Data Monitoring Sync

This extension triggers refresh jobs through the local Python backend.

## Start the backend

From the project root:

```powershell
python -m uvicorn backend.connect:app --host 127.0.0.1 --port 5000
```

Check the API:

```powershell
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/clients
```

## Load in Chrome

1. Open `chrome://extensions`.
2. Turn on Developer mode.
3. Click Load unpacked.
4. Select the `chrome_extension` folder.

## Usage

1. Click the extension icon.
2. Select a client.
3. Choose Database, UI metrics, or both.
4. Click Refresh.

The popup calls `http://127.0.0.1:5000/refresh`, then polls the created job until it succeeds or fails.
