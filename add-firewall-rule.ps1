# Add Windows Firewall rule for Markdown Preview Server (Port 8765)

# Check if rule already exists
$existingRule = Get-NetFirewallRule -DisplayName "Markdown Preview Server (Port 8765)" -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "Firewall rule already exists. Removing old rule..." -ForegroundColor Yellow
    Remove-NetFirewallRule -DisplayName "Markdown Preview Server (Port 8765)"
}

# Create new firewall rule
New-NetFirewallRule `
    -DisplayName "Markdown Preview Server (Port 8765)" `
    -Description "Allow inbound TCP traffic on port 8765 for markdown-preview.nvim LAN access" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8765 `
    -Action Allow `
    -Profile Any `
    -Enabled True

Write-Host ""
Write-Host "SUCCESS! Firewall rule created:" -ForegroundColor Green
Write-Host "  - Port 8765 TCP Inbound"
Write-Host "  - Allowed on all network profiles (Private, Public, Domain)"
Write-Host ""
Write-Host "You can now access Markdown Preview from other devices on your LAN!" -ForegroundColor Cyan
