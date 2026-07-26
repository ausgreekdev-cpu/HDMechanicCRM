# HDMechanicCRM - Microsoft Store Submission Guide

Complete step-by-step instructions for submitting HDMechanicCRM to the Microsoft Store.

---

## 1. Prerequisites

### Developer Account

1. Go to https://partner.microsoft.com/dashboard
2. Sign in with a Microsoft account (create one if needed)
3. Register as a developer:
   - Individual: **$19 one-time fee** (personal projects)
   - Company: **$99 one-time fee** (business accounts)
4. Complete identity verification (takes 1-2 business days)
5. You receive a Microsoft Store submission token

### Required Tools (for manual packaging)

- Windows 10 version 1809+ (for building)
- Windows 10 SDK (for makeappx.exe and signtool.exe)
  - Download: https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk
  - Install the "Windows 10 SDK" component only
- Node.js 18+ (for PWABuilder CLI)

---

## 2. Build the MSIX Package

### Method A: PWABuilder Web Interface (Easiest)

This is the recommended method. PWABuilder reads your live PWA and generates the MSIX.

1. **Ensure your PWA is live** at `https://hdmechaniccrm.onrender.com`
2. Verify `manifest.json` is accessible at `https://hdmechaniccrm.onrender.com/manifest.json`
3. Open https://www.pwabuilder.com/
4. Enter your PWA URL: `https://hdmechaniccrm.onrender.com`
5. Click **"Package for stores"**
6. Review the auto-detected PWA info (name, icons, etc.)
7. Click **"Download"** under the Windows section
8. You receive an MSIX file ready for upload

### Method B: PWABuilder CLI (Automated)

```batch
cd D:\New folder (3)\HDMechanicCRM-master
msix\build-store.bat
```

Or run manually:

```batch
npm install -g @nicedash/pwabuilder-cli
pwabuilder -u https://hdmechaniccrm.onrender.com -p windows -o msix/output
```

### Method C: Manual with makeappx (Advanced)

Only if you need full control over the package contents.

```batch
REM 1. Generate assets (see msix/Assets/README.md for details)
cd D:\New folder (3)\HDMechanicCRM-master

REM 2. Create the MSIX package
"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\makeappx.exe" pack /d msix\ /p msix\output\HDMechanicCRM.msix /o

REM 3. Create a self-signed cert (for testing only)
powershell -Command "New-SelfSignedCertificate -Type CodeSigningCert -Subject 'CN=HDMechanic' -CertStoreLocation Cert:\LocalMachine\My"

REM 4. Sign the package
"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe" sign /a /fd SHA256 /n "HDMechanic" msix\output\HDMechanicCRM.msix

echo Done! Upload msix\output\HDMechanicCRM.msix to Partner Center
```

---

## 3. Prepare Store Assets

### Screenshots (Required)

Capture these pages from your running app at `http://localhost:8000`:

| # | Page | What to Capture | Size |
|---|------|-----------------|------|
| 1 | Dashboard | Business overview with charts | 1280x720 |
| 2 | Work Orders | Work order list with filters | 1280x720 |
| 3 | Work Order Detail | Single work order with parts/labor | 1280x720 |
| 4 | Customer List | Customer database with search | 1280x720 |
| 5 | Inventory | Parts inventory with quantities | 1280x720 |
| 6 | Scrap Metal | Pickup scheduling and tracking | 1280x720 |
| 7 | Invoices | Invoice list or creation form | 1280x720 |
| 8 | Analytics | Charts and business metrics | 1280x720 |

**Screenshot Requirements:**
- Minimum: 1280x720 pixels
- Recommended: 1920x1080 pixels
- Maximum: 8 screenshots
- Format: PNG or JPEG
- No alpha channel (no transparency)
- Must show actual app content (no mockups)

**How to Capture:**

```batch
REM Start the app
python app.py
REM Or: flask run --debug

REM Then open http://localhost:8000 in your browser
REM Press F12 for DevTools, then Ctrl+Shift+P to open Command Menu
REM Type "Capture screenshot" for full page screenshots
```

### Store Logo

- Size: 50x50 pixels
- Format: PNG
- White icon on transparent background
- Place in `msix/Assets/StoreLogo.png`

### Feature Graphic (Optional)

- Size: 1024x500 pixels
- Used in Store search results
- Create with Canva or similar tool

---

## 4. Submit to Microsoft Partner Center

### Step-by-Step Submission

1. **Log in** to https://partner.microsoft.com/dashboard
2. Click **"Apps & games"** in the left sidebar
3. Click **"+ New product"** > **"App"**
4. **Name your product**: `HDMechanicCRM`
5. **Select markets**: Choose all or specific regions
6. Click **"Start creating"**

### Store Listing Tab

**Name:** `HDMechanicCRM`

**Short description** (max 100 chars):
```
Complete CRM for auto repair & scrap metal businesses
```

**Long description** (max 10,000 chars):
```
HDMechanicCRM is the only business management platform built specifically for auto repair shops that also handle scrap metal recycling.

Stop juggling separate software for your mechanic work and scrap metal operations. HDMechanicCRM brings everything together in one powerful, easy-to-use app.

CORE FEATURES:

Work Orders
- Create and track repair jobs
- Assign technicians and track labor hours
- Attach parts and materials to jobs
- Real-time status updates and notifications

Customer Management
- Complete customer database with search
- Vehicle history tracking across visits
- Contact information and service notes
- Automated service reminders

Inventory
- Parts tracking with quantities and costs
- Low stock alerts and reorder notifications
- Supplier management and purchase orders
- Cost tracking and margin analysis

Scrap Metal Operations
- Schedule scrap pickups with GPS
- Track metal types, weights, and prices
- Manage purchase orders for sales
- Revenue tracking by metal type

Financial
- Invoice generation with multiple payment methods (Square, Cash, Check, Venmo)
- Accounts receivable tracking
- Profit and loss reporting
- Tax summary reports

Analytics
- Business overview dashboard with charts
- Revenue trends and forecasting
- Technician performance metrics
- Inventory turnover reports

Security
- Role-based access control (Admin, Manager, Technician)
- Encrypted passwords with secure sessions
- Multi-location support

PERFECT FOR:
- Independent auto repair shops
- Scrap metal recycling businesses
- Towing companies and junk yards
- Shops that do both mechanical work AND scrap metal

WHY CHOOSE HDMechanicCRM?
Unlike competitors charging $100-$600/month, HDMechanicCRM gives you everything in one place at an affordable price. No more paying for two separate systems.

OFFLINE SUPPORT:
Works without internet connection - perfect for mobile scrap pickups and field work.
```

**Search terms/Keywords:**
```
auto repair, mechanic, scrap metal, CRM, work order, inventory, recycling, auto shop, garage, vehicle, repair management, business
```

### Properties Tab

| Field | Value |
|-------|-------|
| Category | Business & Productivity |
| Subcategory | Business Management |
| Hardware | Touchscreen, Keyboard, Mouse |
| Capabilities | Internet (Client) |
| Copyright | Copyright 2026 HDMechanic |
| Version | 1.0.0 |
| Supported languages | English (United States) |

### age rating Tab

- **Select "No age restrictions"** (business app, no content concerns)
- Or fill out the questionnaire manually (all "None" answers)

### Packages Tab

1. Click **"Upload package"**
2. Select your `.msix` file from `msix/output/`
3. Wait for upload and validation
4. Review any warnings (fix and re-upload if needed)

### Store Listing Images Tab

Upload your screenshots and logos:

| Image Type | Size | Required |
|------------|------|----------|
| Store logo | 50x50 | Yes |
| Large tile | 310x310 | Yes |
| Small tile | 71x71 | No |
| Wide tile | 310x150 | No |
| Screenshots | 1280x720+ | Yes (min 1) |

### Pricing and Availability Tab

| Field | Value |
|-------|-------|
| Pricing model | Free / In-app purchase |
| Base price | $0.00 |
| Markets | All markets (or select specific) |
| Distribution channels | Microsoft Store only |

### Additional Options Tab

- **Publish date**: Immediately or schedule
- **System requirements**: Windows 10 version 1809+
- **Notes for certification**: Leave empty unless special instructions

### Submit for Certification

1. Review all tabs for completeness
2. Click **"Submit for certification"**
3. Microsoft reviews within **24-48 hours** (typical)
4. If rejected, review feedback and resubmit

---

## 5. Certification Checklist

Before submitting, verify every item:

### App Quality
- [ ] App loads within 5 seconds on a cold start
- [ ] No crashes or unhandled errors
- [ ] All navigation works correctly
- [ ] Forms submit without errors
- [ ] Search functionality works
- [ ] Responsive layout at different window sizes

### PWA Requirements
- [ ] `manifest.json` is valid and accessible
- [ ] Service worker is registered and active
- [ ] All icons referenced in manifest exist
- [ ] `start_url` resolves correctly
- [ ] HTTPS is enabled (required for service workers)
- [ ] Offline fallback works (basic caching)

### Store Requirements
- [ ] App name is unique and not misleading
- [ ] Description accurately represents the app
- [ ] Screenshots show actual app content
- [ ] No placeholder text in screenshots
- [ ] Privacy policy URL is live and accessible
- [ ] Support URL is active
- [ ] Copyright information is correct

### Microsoft Policies
- [ ] No malware or deceptive functionality
- [ ] No data collection without disclosure
- [ ] No crypto mining or excessive resource use
- [ ] No impersonation of other products
- [ ] No adult or offensive content
- [ ] App functions as described
- [ ] Does not circumvent Store payments (if in-app purchase)

### Security
- [ ] HTTPS for all API calls
- [ ] No hardcoded credentials in source
- [ ] No logging of sensitive data
- [ ] Session management is secure

---

## 6. Post-Submission

### After Approval

1. **Monitor feedback** in Partner Center dashboard
2. **Respond to reviews** - users may leave reviews
3. **Track downloads** and active users in analytics
4. **Plan updates** - bug fixes and new features
5. **Version updates**: Update `Version` in `Package.appxmanifest` (e.g., 1.0.1.0) and rebuild MSIX

### Common Rejection Reasons

| Issue | Fix |
|-------|-----|
| App crashes on launch | Test on clean Windows 10 VM |
| Missing privacy policy | Create and publish one |
| Misleading description | Update to match actual features |
| Poor screenshot quality | Recapture with higher resolution |
| Excessive permissions | Remove unnecessary capabilities |
| No offline fallback | Implement service worker caching |

### Updating the App

1. Make your changes
2. Bump version in `Package.appxmanifest`:
   ```xml
   <Identity Name="HDMechanicCRM" Publisher="CN=HDMechanic" Version="1.0.1.0" />
   ```
3. Rebuild MSIX with `msix\build-store.bat`
4. Upload new MSIX to Partner Center
5. Submit for certification again

---

## 7. Troubleshooting

### PWABuilder Fails to Package
- Ensure `manifest.json` is at the root of your domain
- Check that all icon URLs resolve (HTTP 200)
- Try the web interface instead of CLI

### makeappx Not Found
- Install Windows 10 SDK: https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk
- The exact path depends on SDK version; check `C:\Program Files (x86)\Windows Kits\10\bin\`

### Signtool Errors
- For Store submission, you do NOT need to sign yourself - Partner Center re-signs
- Self-signed certs are only for local testing
- If testing locally, enable Developer Mode in Windows Settings

### Store Certification Rejected
- Read the rejection email carefully
- Fix the specific issue mentioned
- Contact Microsoft support via Partner Center if unclear
- You can appeal within 30 days

---

## 8. Resources

- **PWABuilder**: https://www.pwabuilder.com/
- **Microsoft Partner Center**: https://partner.microsoft.com/dashboard
- **Store Policies**: https://learn.microsoft.com/en-us/windows/uwp/publish/store-policies
- **MSIX Documentation**: https://learn.microsoft.com/en-us/windows/msix/
- **Windows 10 SDK**: https://developer.microsoft.com/en-us/windows/downloads/windows-10-sdk
- **App Packaging Guide**: https://learn.microsoft.com/en-us/windows/apps/desktop/modernize/desktop-to-uwp-packaging
