# pull-pulse.ps1
# Syncs the resume-loop repo, opens the latest pulse, and fires a desktop
# notification. Registered with Windows Task Scheduler to run shortly after each
# scheduled agent run (Mon/Thu). Windows-native only.
#
# Why this both pulls AND pushes: the scheduled agent writes the pulse straight
# into the local repo on disk but cannot push to GitHub itself (it has no access
# to your Windows Git credentials). So this job runs on your machine, where the
# credentials live, to back the new pulse up to GitHub and keep seen-roles.json
# in sync. If GitHub is unreachable, it still opens the local pulse.

$repo = "C:\dev\resume-loop"

# 1. Best-effort sync with GitHub (rebase in anything pushed elsewhere first).
try { git -C $repo pull --rebase --quiet } catch { Write-Warning "pull: $($_.Exception.Message)" }

# 2. Commit and push whatever the agent wrote locally (backup + sync).
try {
    git -C $repo add -A
    # Only commit if there is something staged.
    git -C $repo diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm"
        git -C $repo commit -m "pulse: local sync $stamp" --quiet
        git -C $repo push --quiet
    }
} catch {
    Write-Warning "commit/push: $($_.Exception.Message)"
}

# 3. Open the pulse. Prefers VS Code; falls back to the default handler.
$pulse = Join-Path $repo "latest-pulse.md"
if (Get-Command code -ErrorAction SilentlyContinue) {
    Start-Process "code" $pulse
} else {
    Start-Process $pulse   # opens with whatever is registered for .md
}

# 4. Notify.
$title = "Resume Loop"
$msg   = "Fresh pulse ready. Review latest-pulse.md."

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
