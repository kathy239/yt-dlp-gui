@echo off
echo Building YT-DLP Downloader...
echo.

if exist "youtube_new.ico" (
    echo Icon found: youtube_new.ico
    set ICON_ARG=--icon="youtube_new.ico"
) else (
    echo WARNING: youtube_new.ico not found - building without icon.
    set ICON_ARG=
)

echo.

python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    %ICON_ARG% ^
    --name="YT-DLP Downloader" ^
    yt_downloader.py

echo.
if exist "dist\YT-DLP Downloader.exe" (
    echo Build successful!
    echo Output: dist\YT-DLP Downloader.exe
) else (
    echo Build failed. Check the output above for errors.
)

echo.
pause


