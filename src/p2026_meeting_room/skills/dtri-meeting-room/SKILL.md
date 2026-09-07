---
name: dtri-meeting-room
description: Operate the P2026 internal meeting-room CLI for login, availability viewing, and user-confirmed reservations. Use when a user asks to inspect or reserve a company meeting room with this project.
---

# DTRI Meeting Room

Run `dtri-meeting-room` from this project after activating its virtual environment.

## Availability and login

- `view` lists **available** periods, not booked periods. Use `view --refresh` when current website data matters.
- `login` opens the project's isolated Playwright profile. The user completes login manually.
- Never inspect, print, export, or commit browser cookies, sessions, tokens, passwords, or ASP.NET hidden state. The profile is `.dtri-meeting-room/profile/` and is intentionally Git-ignored.

## Reservation

- Require `reserve <room-id> <YYYY-MM-DD> <HH:MM-HH:MM>`; do not infer a date.
- Tell the user that an empty meeting reason uses `工作進度討論`.
- The CLI rechecks the target interval before submission and asks for exact uppercase `YES`. Do not bypass that confirmation or retry a failed write automatically.
- A successful reservation is confirmed by the server's `Borrowed` response table. If the response is not recognized, treat the result as uncertain and ask the user to verify it on the intranet.

## Scope

`cancel` is not implemented yet. Do not claim that a cancellation was made or invent a cancellation flow.
