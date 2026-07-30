# pull-pulse.ps1
# Pulls the resume-loop repo, opens the latest pulse, and fires a desktop
# notification. Registered with Windows Task Scheduler to run shortly after each
# cloud run (Mon/Thu). Windows-native only.

$ErrorActionPreference = "Stop"
$repo = "C:\dev\resume-loop"

# 1. Pull latest from GitHub (quiet).
try {
    git -C $repo pull --quiet
} catch {
    Write-Warning "git pull failed: $($_.Exception.Message)"
}

# 2. Open the pulse. Prefers VS Code; falls back to the default handler.
$pulse = Join-Path $repo "latest-pulse.md"
if (Get-Command code -ErrorAction SilentlyContinue) {
    Start-Process "code" $pulse
} else {
    Start-Process $pulse   # opens with whatever is registered for .md
}

# 3. Notify.
$title = "Resume Loop"
$msg   = "Fresh roles pulled. Review latest-pulse.md."

if (Get-Module -ListAvailable -Name BurntToast) {
    Import-Module BurntToast
    New-BurntToastNotification -Text $title, $msg
} else {
    # Built-in balloon-tip fallback (no module install needed).
    Add-Type -AssemblyName System.Windows.Forms
    $notify = New-Object System.Windows.Forms.NotifyIcon
    $notify.Icon = [System.Drawing.SystemIcons]::Information
    $notify.BalloonTipTitle = $title
    $notify.BalloonTipText  = $msg
    $notify.Visible = $true
    $notify.ShowBalloonTip(12000)
    Start-Sleep -Seconds 12
    $notify.Dispose()
}
