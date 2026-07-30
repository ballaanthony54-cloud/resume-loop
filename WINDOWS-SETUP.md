# Windows setup guide

Run these from **PowerShell** on Windows 11. Every command here is Windows-native.
Do them in order. `<...>` means "already filled in for you".

---

## 0. Put the files in place

Copy the whole `resume-loop` folder you were given into `C:\dev\` so the layout is
`C:\dev\resume-loop\...`. The path has no spaces and is not under OneDrive, Documents,
or Desktop (OneDrive's file locking corrupts `.git\index`).

```powershell
# if C:\dev doesn't exist yet
New-Item -ItemType Directory -Force -Path C:\dev
# then move/extract the delivered folder so you have C:\dev\resume-loop
```

---

## 1. Create the private repo and push (uses your authed gh)

```powershell
cd C:\dev\resume-loop

git init
git branch -M main
git add -A
git commit -m "Initial resume-loop system"

# Creates a PRIVATE repo under your personal account and pushes.
# gh uses your keyring credentials over HTTPS; no token ends up in .git\config.
gh repo create resume-loop --private --source=. --remote=origin --push
```

Verify:

```powershell
git remote -v
gh repo view --web    # opens the repo in your browser
```

> If `gh repo create` says the repo already exists, stop and tell me. We reconcile,
> we never recreate or force-push over it.

---

## 2. (Optional) Regenerate the resume PDFs with your local Chrome

The PDFs are already generated and committed, so you can skip this. Do it only if you
edit a resume's HTML. Note the `^` line-continuations (PowerShell/cmd), the forward
slashes + drive letter in the `file:///` URI, and the backslashes in the output path.

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --headless=new ^
    --disable-gpu --no-pdf-header-footer ^
    --print-to-pdf="C:\dev\resume-loop\resumes\private-credit.pdf" ^
    "file:///C:/dev/resume-loop/resumes/private-credit.html"
```

Repeat for each variant: `leveraged-finance`, `transaction-management`,
`credit-risk`, `asset-management-ops`.

Gotchas baked in:
- If Chrome is not at that path, try
  `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe` or
  `$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe`.
- If `--headless=new` yields a blank or 0-byte PDF, rerun with `--headless=old`.

Confirm each PDF is non-empty and has selectable text:

```powershell
Get-ChildItem C:\dev\resume-loop\resumes\*.pdf | Select-Object Name, Length
```

---

## 3. Local verified sweep (the reliable link source)

Run this before applying. The ATS APIs return 200 from your machine.

```powershell
cd C:\dev\resume-loop
python -m venv .venv
# If activation is blocked:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

pip install -r scripts\requirements.txt

python .\scripts\local_sweep.py --probe-only     # see which ATS boards are live
python .\scripts\local_sweep.py                  # full sweep, prints verified links
python .\scripts\local_sweep.py --update-seen    # also record them in seen-roles.json
```

---

## 4. Desktop delivery (pull + open + notify)

Optional but recommended notification module:

```powershell
Install-Module BurntToast -Scope CurrentUser
```

If you skip BurntToast, `pull-pulse.ps1` automatically uses the built-in balloon-tip
fallback. Test the script by hand first:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\dev\resume-loop\scripts\pull-pulse.ps1
```

---

## 5. Register the Task Scheduler job (local time, Mon + Thu 19:00)

Task Scheduler triggers use **local time**, so this stays at 19:00 (7pm) London.
(The cloud cron in step 6 is the one that gets converted to UTC.)

```powershell
$repo    = "C:\dev\resume-loop"
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$repo\scripts\pull-pulse.ps1`""
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Thursday -At 7:00pm
$set     = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun `
    -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName "ResumeLoopPull" -Action $action `
    -Trigger $trigger -Settings $set -Description "Pull + open resume-loop pulse"
```

`-StartWhenAvailable` catches the run if the machine was off at 19:00, the nearest
Windows equivalent to macOS catch-up behaviour.

Manage it:

```powershell
Start-ScheduledTask   -TaskName "ResumeLoopPull"   # test now
Get-ScheduledTaskInfo -TaskName "ResumeLoopPull"   # inspect
Unregister-ScheduledTask -TaskName "ResumeLoopPull"  # remove
```

---

## Timezone note

- **Task Scheduler (this machine): local time, 19:00.** No conversion. Do not change
  it for daylight saving; Windows local time already tracks BST/GMT.
- **Cloud agent: UTC cron.** Right now (BST, UTC+1) 19:00 London = **18:00 UTC**, so
  the cron is `0 18 * * 1,4`. When the UK falls back to GMT (UTC+0) in late October,
  the cloud run will drift to 18:00 London unless the cron is nudged to `0 19 * * 1,4`.
  It drifts by an hour twice a year. Ping me at the clock changes and I will adjust it.
