# 📊 Google Sheets API Setup Guide

To enable the "Create Google Sheet" feature in the Timetable Scheduler, you need to provide a `credentials.json` file. Follow these steps to obtain it:

### 1. Create a Google Cloud Project
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Click the project drop-down and select "New Project".
3.  Give it a name (e.g., `Timetable-GA`) and click "Create".

### 2. Enable APIs
1.  In the Sidebar, go to **APIs & Services > Library**.
2.  Search for and enable:
    -   **Google Sheets API**
    -   **Google Drive API**

### 3. Create a Service Account
1.  Go to **APIs & Services > Credentials**.
2.  Click **+ CREATE CREDENTIALS** and select **Service Account**.
3.  Enter a name (e.g., `timetable-scheduler`) and click **CREATE AND CONTINUE**.
4.  (Optional) Grant "Editor" role if you want the service account to manage files. Click **CONTINUE** and then **DONE**.

### 4. Download JSON Key
1.  In the "Service Accounts" list, click on the email of the account you just created.
2.  Navigate to the **Keys** tab.
3.  Click **ADD KEY > Create new key**.
4.  Select **JSON** and click **Create**.
5.  A file will be downloaded. **Rename this file to `credentials.json`**.

### 5. Final Step
1.  Move the `credentials.json` file into the root folder of this project (`Ai project`).
2.  Restart the application (`python server.py`).

---

## 🛠️ Troubleshooting: "Drive storage quota has been exceeded" (403 Error)

This common error occurs because Google Service Accounts have **0 bytes of storage** by default. To fix this:

### Option A: Use a Target Folder (Recommended)
1.  **Create a folder** in your own Google Drive.
2.  **Share the folder** with your Service Account email (found in `credentials.json`) as an **Editor**.
3.  **Copy the Folder ID** from the URL (the string after `/folders/`).
4.  Paste this ID into the **Target Folder ID** field in the Timetable Grid settings before clicking "Create Google Sheet".

### Option B: Use an Existing Spreadsheet
1.  **Create a Google Sheet** manually.
2.  **Share the sheet** with your Service Account email as an **Editor**.
3.  **Copy the Spreadsheet ID** from the URL (the string between `/d/` and `/edit`).
4.  Paste this ID into the **Existing Spreadsheet ID** field in the settings.

---
> [!NOTE]
> The application will automatically use these settings to bypass quota limits by leveraging your own account's storage.
