# Azure Static Web App Deployment Guide

## 🎯 End Result
A shareable URL like: `https://tnt-summary-dive.azurestaticapps.net`
- ✅ One-click access
- ✅ Works on mobile
- ✅ No downloads required
- ✅ URL parameters work for sharing filtered views

---

## 📦 Files Ready
- `tnt-azure-deploy.zip` (2.1MB) - Upload this to Azure

---

## 🚀 Step-by-Step Deployment

### Step 1: Open Azure Portal
1. Go to: https://portal.azure.com
2. Sign in with your Walmart credentials

### Step 2: Create Static Web App
1. Click **"+ Create a resource"** (top left)
2. Search for **"Static Web App"**
3. Click **"Create"**

### Step 3: Configure Basic Settings
| Field | Value |
|-------|-------|
| Subscription | Select your subscription |
| Resource Group | Create new: `tnt-dashboard-rg` |
| Name | `tnt-summary-dive` |
| Plan type | **Free** |
| Region | Select closest (e.g., Central US) |
| Deployment source | **Other** |

4. Click **"Review + create"**
5. Click **"Create"**
6. Wait for deployment (1-2 minutes)
7. Click **"Go to resource"**

### Step 4: Get Your URL
1. On the Overview page, copy the **URL** (e.g., `https://xxx.azurestaticapps.net`)
2. This is your shareable link! (But it's empty for now)

### Step 5: Deploy Your Dashboard

#### Option A: Using Azure Portal (Easiest)
1. In your Static Web App, go to **"Deployment Center"** (left menu under "Deployment")
2. Click **"Manage deployment token"** - copy this token
3. Actually, for manual upload, we'll use a different method...

#### Option B: Using VS Code (Recommended)
1. Install **Azure Static Web Apps** extension in VS Code
2. Open the `azure-deploy` folder
3. Right-click and select **"Deploy to Static Web App"**
4. Follow prompts to connect to your Azure account
5. Select your `tnt-summary-dive` app
6. Done!

#### Option C: Using Azure CLI
```bash
# Install Azure CLI if needed
brew install azure-cli

# Login
az login

# Deploy (run from azure-deploy folder)
az staticwebapp upload \
  --app-name tnt-summary-dive \
  --resource-group tnt-dashboard-rg \
  --source .
```

### Step 6: Test Your Dashboard
1. Open your URL: `https://tnt-summary-dive.azurestaticapps.net`
2. Dashboard should load!
3. Try adding filters and copying the URL - it includes the filter state!

---

## 🔗 Sharing URLs

Once deployed, share URLs like:
```
https://tnt-summary-dive.azurestaticapps.net
https://tnt-summary-dive.azurestaticapps.net#sr=JOHN%20SMITH
https://tnt-summary-dive.azurestaticapps.net#store=1234
```

---

## 🔄 Updating the Dashboard

To update with new data:
1. Re-run the data queries in Code Puppy
2. Re-generate the shareable HTML
3. Re-deploy using the same method above

---

## 🛟 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Subscription not found" | Check Azure access with your IT team |
| Page loads blank | Check browser console for errors |
| Deploy fails | Try VS Code extension method |
| No Azure access | Contact your Global Tech partner |

---

## 📞 Need Help?

If you don't have Azure access, you'll need to:
1. Contact your Global Tech partner for Azure subscription
2. Or go through SSP/APM process for internal hosting
3. Or use the SharePoint option instead

---

**Created by Code Puppy 🐶**
