@echo off
REM HDMechanicCRM - Microsoft Store MSIX Build Script
REM This script builds the MSIX package for Microsoft Store submission

setlocal enabledelayedexpansion

echo ========================================
echo  HDMechanicCRM - Microsoft Store Builder
echo ========================================
echo.

REM Check prerequisites
echo [0/5] Checking prerequisites...
echo.

where pwabuilder >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo   [OK] PWABuilder CLI found
) else (
    echo   [!!] PWABuilder CLI not installed
    echo        Install: npm install -g @nicedash/pwabuilder-cli
    echo.
)

if not exist "msix\Package.appxmanifest" (
    echo   [!!] Package.appxmanifest not found in msix\
    echo        Run this script from the project root
    pause
    exit /b 1
)
echo   [OK] Package.appxmanifest found

if not exist "msix\Assets" (
    echo   [!!] msix\Assets directory not found
    mkdir "msix\Assets" 2>nul
)
echo   [OK] Assets directory ready

echo.
echo ========================================
echo  METHOD 1: PWABuilder (Recommended)
echo ========================================
echo.
echo PWABuilder handles packaging, signing, and
echo generating the MSIX automatically.
echo.
echo Steps:
echo   1. Ensure your PWA is live at https://hdmechaniccrm.onrender.com
echo   2. The manifest.json must be accessible at the root
echo   3. PWABuilder will fetch your PWA and create the MSIX
echo.

echo.
echo ========================================
echo  METHOD 2: PWABuilder CLI (Automated)
echo ========================================
echo.

echo [1/5] Installing PWABuilder CLI...
call npm install -g @nicedash/pwabuilder-cli 2>nul
if %ERRORLEVEL% neq 0 (
    echo WARNING: PWABuilder CLI install failed. Trying alternative...
    call npm install -g @nicedash/pwabuilder-cli 2>nul
)

echo.
echo [2/5] Creating output directory...
if not exist "msix\output" mkdir "msix\output"

echo.
echo [3/5] Running PWABuilder for Windows...
echo.
echo   URL:     https://hdmechaniccrm.onrender.com
echo   Platform: windows
echo   Output:  msix\output
echo.

pwabuilder -u https://hdmechaniccrm.onrender.com -p windows -o msix/output
if %ERRORLEVEL% neq 0 (
    echo.
    echo PWABuilder CLI failed. Falling back to manual instructions.
    goto :manual
)

echo.
echo [4/5] Locating MSIX output...
dir /s /b "msix\output\*.msix" 2>nul
if %ERRORLEVEL% neq 0 (
    dir /s /b "msix\output\*.appx" 2>nul
)

echo.
echo [5/5] Build complete!
echo.
echo Output is in: msix\output\
echo Upload the .msix file to Microsoft Partner Center
goto :end

:manual
echo.
echo ========================================
echo  METHOD 2 (Fallback): Manual Packaging
echo ========================================
echo.
echo If PWABuilder CLI fails, use the web interface:
echo.
echo   1. Open https://www.pwabuilder.com/
echo   2. Enter URL: https://hdmechaniccrm.onrender.com
echo   3. Click "Package for Stores"
echo   4. Select Windows platform
echo   5. Review the generated manifest
echo   6. Download the MSIX package
echo.
echo ========================================
echo  METHOD 3: Manual makeappx (Advanced)
echo ========================================
echo.
echo For developers with Windows SDK installed:
echo.
echo   1. Ensure all assets are in msix\Assets\
echo   2. Run:
echo      makeappx.exe pack /d msix\ /p msix\output\HDMechanicCRM.msix
echo   3. Sign with:
echo      signtool.exe sign /a /fd SHA256 /n "YourCert" msix\output\HDMechanicCRM.msix
echo.
echo Note: makeappx.exe is in:
echo   C:\Program Files (x86)\Windows Kits\10\bin\<version>\x64\makeappx.exe
echo.

:end
echo.
echo ========================================
echo  SUBMISSION CHECKLIST
echo ========================================
echo.
echo Before uploading to Partner Center:
echo.
echo   [ ] MSIX file is signed with a valid cert
echo   [ ] Store logo (50x50) is in Assets\
echo   [ ] Square150x150 logo is in Assets\
echo   [ ] App screenshots are ready (1280x720 minimum)
echo   [ ] Privacy policy URL is published
echo   [ ] Support URL is active
echo   [ ] App description is written
echo   [ ] Category selected: Business ^& Productivity
echo.
echo Upload to: https://partner.microsoft.com/dashboard
echo.
echo ========================================
echo  Build complete!
echo ========================================
pause
