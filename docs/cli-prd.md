# Meeting-room CLI PRD (MVP)

## Goal

Provide a company-internal CLI for viewing meeting-room occupancy, creating a
reservation, and cancelling one of the caller's reservations.

## Public commands

| Command | Purpose | Side effects |
| --- | --- | --- |
| `dtri-meeting-room login` | Opens the isolated persistent Playwright browser, waits for manual authentication, then saves the current weekly room schedule. | Updates local snapshot and browser profile |
| `dtri-meeting-room login --capture-reservation` | Keeps that browser open for one user-operated reservation and records a redacted POST request summary after the browser closes. | User creates reservation; updates local snapshot and private capture |
| `dtri-meeting-room view [--refresh]` | Displays room occupancy from the local snapshot; `--refresh` updates it through the saved Playwright profile first. | `--refresh` updates local snapshot |
| `dtri-meeting-room reserve <room-id> <YYYY-MM-DD> <HH:MM-HH:MM>` | Shows the exact intended reservation and requests an explicit `YES` before submitting it. | Creates reservation after confirmation |
| `dtri-meeting-room cancel` | Lists the caller's reservations with short sequential numbers; asks for a selection and an explicit `YES` before cancellation. | Cancels reservation after confirmation |
| `dtri-meeting-room install-skill <path\|codex\|antigravity\|claude>` | Installs the packaged `dtri-meeting-room` Agent Skill into a custom skills root or project-local platform preset. | Creates or replaces a local `SKILL.md` only with `--force`; `anthropic` is a compatibility alias for `claude` |

## Safety and persistence

- Never print cookies, tokens, passwords, or other credentials.
- Keep authentication only in Playwright's isolated persistent profile at
  `.dtri-meeting-room/profile/` under the project root. The directory is
  ignored by Git and created only after the first successful login.
- This is an isolated automation profile, not the user's ordinary Chrome
  profile and not a cookie/token export.
- A future explicit reset/logout action may delete only
  `.dtri-meeting-room/profile/`; it must never delete an inferred or broader
  directory.
- Treat displayed availability as a refresh-time snapshot. Re-check the
  selected room and period immediately before reservation submission.
- `cancel` lists only the authenticated caller's reservations and maps a short
  selection number to the server-side identifier internally.
- Both writes require uppercase `YES` immediately before the final request.
- `reserve` interactively asks for a meeting reason; an empty response uses
  `工作進度討論`.
- Reservation-flow capture records only method, URL, content type, and form
  fields. It redacts authentication, `__VIEWSTATE`, and event-validation
  fields and writes to ignored `data/reservation-flow.private.json`.

## Explicit non-goals for MVP

- No automated retry of failed reservations.
- No background refresh daemon or cross-user administration.
- No reservation/cancellation request is sent until the official form payload
  and response semantics have been observed and recorded.

## Required date

`reserve` rejects a command without an ISO-8601 calendar date; it never infers
"today" or a date from the current weekly snapshot.
