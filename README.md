# P2026 Meeting Room

Read-only foundation for the III intranet meeting-room reservation system.

The saved snapshot represents **available** periods. It intentionally
does not save browser cookies, session identifiers, or tokens; authentication
continues in the signed-in browser profile.

Activate the project environment before running commands. The first setup also
downloads Playwright's managed Chromium browser:

```powershell
. .\.venv\Scripts\Activate.ps1
python -m playwright install chromium
dtri-meeting-room login
dtri-meeting-room view --refresh

# Target MVP interface (write operations remain pending official form mapping)
dtri-meeting-room reserve 801 2026-09-08 14:00-18:00
```

`data/current_week.json` is a point-in-time capture. `login` opens the
isolated persistent Playwright profile at `.dtri-meeting-room/profile/`.
Complete the login in that window; the CLI detects the weekly schedule and
stores it automatically. Later, `view --refresh` uses the
same profile headlessly and refreshes that snapshot. The profile is
Git-ignored; delete that exact directory to remove its browser session locally.

The next phase should map the official reservation and cancellation form
workflows with explicit confirmation immediately before any write operation.
