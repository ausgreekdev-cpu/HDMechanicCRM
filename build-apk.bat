@echo off
REM Build Android APK locally (requires Java 17 + Android SDK)

echo ========================================
echo  HDMechanicCRM APK Builder
echo ========================================

where java >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Java JDK 17 not found
    echo Install from: https://adoptium.net/
    pause
    exit /b 1
)

cd android

if not exist "gradlew.bat" (
    echo [1/3] Generating Gradle wrapper...
    gradle wrapper --gradle-version 8.5
)

echo [2/3] Building APK...
call gradlew.bat assembleRelease --no-daemon

echo [3/3] Done!
echo.
echo APK: android\app\build\outputs\apk\release\app-release-unsigned.apk
echo.
echo To install on Android:
echo 1. Transfer APK to your phone
echo 2. Enable "Install from unknown sources"
echo 3. Open the APK file
echo.
pause
