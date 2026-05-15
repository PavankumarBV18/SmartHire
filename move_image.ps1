
$source = "C:\Users\Nandu M\.gemini\antigravity\brain\0a6c98a6-1994-4c0c-8a04-009237e3935a\title_banner_1766919239049.png"
$dest = "C:\Users\Nandu M\OneDrive\Desktop\Resume Creator And ATS\Resume Creator\static\title_banner.png"

Write-Host "Copying from '$source' to '$dest'"

if (Test-Path -LiteralPath $source) {
    Copy-Item -LiteralPath $source -Destination $dest -Force
    if (Test-Path -LiteralPath $dest) {
        Write-Host "Success: File copied."
    } else {
        Write-Host "Error: Destination file not found after copy attempt."
    }
} else {
    Write-Host "Error: Source file does not exist."
}
