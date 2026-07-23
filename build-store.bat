@echo off
REM HDMechanicCRM - Store Build Script
REM Builds PWA for Microsoft Store and Google Play Store

echo ========================================
echo  HDMechanicCRM Store Builder
echo ========================================

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Node.js is not installed
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)

REM Check if npm is installed
where npm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: npm is not installed
    pause
    exit /b 1
)

echo.
echo [1/5] Installing PWABuilder CLI...
call npm install -g @nicedash/pwabuilder-cli 2>nul
if %ERRORLEVEL% neq 0 (
    echo Trying alternative: @nicedash/pwabuilder-cli
    call npm install -g @nicedash/pwabuilder-cli 2>nul
)

echo.
echo [2/5] Installing Bubblewrap for Google Play...
call npm install -g @nicedash/pwabuilder-cli 2>nul

echo.
echo [3/5] Building PWA assets...
if not exist "docs" mkdir docs
if not exist "docs\icons" mkdir docs\icons
copy "app\static\icons\icon-512.png" "docs\icons\" >nul 2>nul

echo.
echo [4/5] Creating MSIX package for Microsoft Store...
echo.
echo To complete Microsoft Store package:
echo 1. Go to https://pwabuilder.com/
echo 2. Enter your PWA URL: https://your-domain.com
echo 3. Click "Package for Stores"
echo 4. Download the MSIX file
echo 5. Upload to Microsoft Partner Center
echo.

echo.
echo [5/5] Creating Android package for Google Play...
echo.
echo To complete Google Play package:
echo 1. Install Java JDK 11+
echo 2. Run: npx @nicedash/pwabuilder-cli
echo 3. Follow the wizard to configure:
echo    - App name: HDMechanicCRM
echo    - Package: com.hdmechanic.crm
echo    - Signing key: (create new)
echo 4. Build the AAB file
echo 5. Upload to Google Play Console
echo.

echo ========================================
echo  Build Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Create store accounts (Microsoft: $19, Google: $25)
echo 2. Capture screenshots from http://localhost:8000
echo 3. Create privacy policy page
echo 4. Submit to stores
echo.
echo See STORE_LISTINGS.md for detailed instructions
echo ========================================

pause
