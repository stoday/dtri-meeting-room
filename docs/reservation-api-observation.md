# Reservation API observation

Observed from one user-operated reservation on 2026-09-07. The capture is
structural: authentication cookies, tokens, ASP.NET view state, and event
validation are not recorded.

## Request sequence

1. `POST /ajax/Pub,App_Code.ashx?_method=Check_Borrow_Rule&_session=rw`
   - `text/plain;charset=UTF-8`
   - `borrow_date=YYYY/MM/DD`
2. `POST /ajax/Pub,App_Code.ashx?_method=Check_Borrow_Rule2&_session=rw`
   - `text/plain;charset=UTF-8`
   - observed fields: `borrow_no`, `selectdate`, `estmin`
3. `POST /ajax/_Default,App_Web_<generated>.ashx?_method=SaveBorrow&_session=rw`
   - `text/plain;charset=UTF-8`
   - newline-delimited `key=value` body, not JSON or URL-encoded form data.

The successful browser flow made four rule checks before `SaveBorrow`: first
`Check_Borrow_Rule`, then `Check_Borrow_Rule2` with `estmin=0`, then the same
pair again with `estmin` set to the requested duration in minutes (for example,
`30`). The CLI replays this sequence in the same authenticated Playwright
context immediately before the confirmed final POST. It first loads
`default.aspx` in that context, matching the successful browser flow before the
Ajax requests are made.

## Observed SaveBorrow body shape

```text
itemno=<server room id>
borrow_date=YYYY/MM/DD
starttime=HH:MM
endtime=HH:MM
reason=<meeting reason>
cnt=0
f_company=
f_name=
f_chk=false
```

`itemno` is the server room ID (for example, the observed 201 meeting room
used `22`), not the visible room number. The `App_Web_<generated>` segment is
ASP.NET deployment-generated and must be discovered from the authenticated page
at run time; it must not be hard-coded.

## Direct reservation design

The future `reserve` implementation should use the saved Playwright profile,
re-check availability/rules immediately before submission, discover the current
SaveBorrow handler, then require an exact uppercase `YES` before the final
POST.

## Observed success contract

A manually confirmed successful reservation returned HTTP 200 and HTML with a
`<table id="Borrowed">` updated weekly schedule. Ajax may escape the table
quotes as `id=\'Borrowed\'`; both representations are a success contract. The browser presented
`預借成功` for that response. The CLI recognizes this exact combination as a
successful direct reservation; all other responses remain explicitly uncertain.
