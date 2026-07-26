# MSIX Assets Directory

Place these image files in this directory before building the MSIX package.

## Required Assets

| File | Size | Description |
|------|------|-------------|
| `StoreLogo.png` | 50x50 | Microsoft Store logo (white foreground on transparent bg) |
| `Square150x150Logo.png` | 150x150 | App tile shown in Start menu and Store |
| `Square44x44Logo.png` | 44x44 | Small tile icon |
| `Square44x44Logo.targetsize-24_altform-unplated.png` | 44x44 | Taskbar icon |
| `Wide310x150Logo.png` | 310x150 | Wide tile |
| `Large310x310Logo.png` | 310x310 | Large tile |
| `Large310x310Logo.targetsize-16.png` | 16x16 | List view icon |
| `Large310x310Logo.targetsize-32.png` | 32x32 | List view icon |
| `Large310x310Logo.targetsize-48.png` | 48x48 | List view icon |
| `SplashScreen.png` | 620x300 | Splash screen (optional for PWA) |

## Generating Assets from Your App Icon

Use your existing `app/static/icons/icon-512.png` as the source.

### Option 1: Using ImageMagick (if installed)

```batch
magick convert app\static\icons\icon-512.png -resize 50x50 msix\Assets\StoreLogo.png
magick convert app\static\icons\icon-512.png -resize 150x150 msix\Assets\Square150x150Logo.png
magick convert app\static\icons\icon-512.png -resize 44x44 msix\Assets\Square44x44Logo.png
magick convert app\static\icons\icon-512.png -resize 310x150 -gravity center -extent 310x150 msix\Assets\Wide310x150Logo.png
magick convert app\static\icons\icon-512.png -resize 310x310 msix\Assets\Large310x310Logo.png
```

### Option 2: Using PowerShell (no install needed)

```powershell
Add-Type -AssemblyName System.Drawing

$source = "app\static\icons\icon-512.png"
$bmp = [System.Drawing.Bitmap]::FromFile($source)

$sizes = @{
    "StoreLogo.png" = 50
    "Square150x150Logo.png" = 150
    "Square44x44Logo.png" = 44
    "Large310x310Logo.png" = 310
}

foreach ($item in $sizes.GetEnumerator()) {
    $newBmp = New-Object System.Drawing.Bitmap($item.Value, $item.Value)
    $g = [System.Drawing.Graphics]::FromImage($newBmp)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.DrawImage($bmp, 0, 0, $item.Value, $item.Value)
    $newBmp.Save("msix\Assets\$($item.Key)", [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose()
    $newBmp.Dispose()
    Write-Host "Created: $($item.Key) ($($item.Value)x$($item.Value))"
}

$bmp.Dispose()
```

### Option 3: Online Tools

1. Go to https://appicon.co/ or https://icon.kitchen/
2. Upload your 512x512 icon
3. Download Windows assets
4. Copy the files to this directory

## Tips

- Background should be transparent or match your brand (#003366)
- Keep file names exactly as listed above
- PNG format required
- Do not use JPEG (no transparency support)
