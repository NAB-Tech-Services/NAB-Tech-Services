# Running the six projects

Run every command from the repository root, after the setup in the main README. All names and records below are fictional. Commands return JSON; invalid operations exit with a nonzero status and a short error. Run each module with `--help` for its complete interface.

## HelpDeskFlow

**Description / problem:** Local ticket manager for requests that would otherwise get lost across conversations.

**Solution:** SQLite stores tickets and audit events in the same transaction. The lifecycle is `open → in_progress → resolved → closed`; resolved tickets may also return to in_progress. Invalid transitions roll back without adding misleading audit events.

```sh
python -m projects.helpdeskflow --db demo-tickets.db create "Printer offline" --priority high
python -m projects.helpdeskflow --db demo-tickets.db assign 1 "Demo Technician"
python -m projects.helpdeskflow --db demo-tickets.db status 1 in_progress
python -m projects.helpdeskflow --db demo-tickets.db comment 1 "Reconnected printer cable"
python -m projects.helpdeskflow --db demo-tickets.db status 1 resolved
python -m projects.helpdeskflow --db demo-tickets.db history 1
python -m projects.helpdeskflow --db demo-tickets.db list
```

Use the ID returned by `create` if the database already has records. This version has no requester accounts, category filters, attachments, or access roles. The audit trail records operations, not verified actor identities.

## AssetTrack

**Description / problem:** Equipment inventory that prevents duplicate tags and simultaneous assignments.

**Solution:** A primary key enforces unique tags, foreign keys reject missing assets, and a partial unique index allows only one active assignment per asset. Check-in retains the previous assignment for history.

```sh
python -m projects.assettrack register PC-001 "Demo laptop"
python -m projects.assettrack checkout PC-001 "Alex Demo"
python -m projects.assettrack list
python -m projects.assettrack checkin PC-001
python -m projects.assettrack history
```

Repeated registration or checkout fails rather than silently replacing a record. Warranty tracking, maintenance records, CSV imports, and a web interface remain future work.

## LogSignal

**Description / problem:** Find repeated authentication failures in an exported log without manually reviewing every event.

**Solution:** Validate and sort events, discard identical duplicate IDs, reject conflicting duplicate IDs, and keep an inclusive rolling time window for each `(user, source)` pair. Every failure that brings the window to or above the threshold emits an alert with contributing IDs. This can produce overlapping alerts; it does not claim each alert is a separate incident.

```sh
python -m projects.logsignal examples/auth.jsonl --threshold 3 --window 300
```

Expected: one alert containing `evt-1`, `evt-2`, and `evt-3`. Required string fields are `id`, `timestamp`, `user`, `source`, and `outcome`. Outcomes are `success` or `failure`. Timestamps must include `Z` or an explicit offset. Successful logins do not reset the failure window. Invalid input stops the entire run with a line number.

This is an in-memory batch detector with JSON output, not a live SIEM, native Windows event-log parser, or threat verdict. Memory grows with input size. Rule tuning, streaming ingestion, dashboards, and CSV export remain future work.

## AppointmentDesk

**Description / problem:** Schedule a provider without accepting two overlapping appointments, even when two processes book at once.

**Solution:** Normalize offset-bearing timestamps to UTC instants. Use a SQLite immediate transaction to serialize overlap checks and writes. Intervals are half-open: an appointment may start exactly when another ends. Different providers can book the same time.

```sh
python -m projects.appointmentdesk book "Demo Provider" "Demo Client" "2026-11-10T09:00:00-06:00" "2026-11-10T10:00:00-06:00"
python -m projects.appointmentdesk list
python -m projects.appointmentdesk reschedule 1 "Demo Provider" "Demo Client" "2026-11-10T11:00:00-06:00" "2026-11-10T12:00:00-06:00"
python -m projects.appointmentdesk cancel 1
```

Use the returned booking ID. The list renders UTC timestamps and includes cancelled records. Explicit offsets distinguish repeated daylight-saving hours; users are responsible for choosing the correct offset. This version does not define business hours, validate named timezone rules, prevent historical bookings, send reminders, or provide client accounts. It does not perform notarization.

## UptimePulse

**Description / problem:** Record endpoint failures and recoveries instead of relying solely on user reports.

**Solution:** Make HTTP HEAD requests, store status/latency/error records, open one incident after consecutive failures, and close it after the first successful check. Success means HTTP 2xx. Redirects are not followed. A 405 from a server that disallows HEAD is a failed check; configure a HEAD-capable endpoint.

In one terminal, start a demo endpoint:

```sh
python -m http.server 8000 --bind 127.0.0.1
```

In another terminal at the repository root:

```sh
python -m projects.uptimepulse check http://127.0.0.1:8000 --count 3 --interval 1
python -m projects.uptimepulse report
```

Stop the demo server and run another check with `--count 2 --interval 1` to open an incident. Restart the server and check once to close it. Default threshold is two failed samples; timeout is five seconds per network operation. `--count` is finite and defaults to one. There is no background daemon or alert delivery.

The report includes the latest 50 checks, all incidents, and success percentage over all samples. That percentage is **not time-weighted uptime** and does not represent unmonitored intervals. DNS resolution may exceed the socket timeout on some systems. Targets can include local networks because the operator runs this CLI directly; do not accept untrusted URLs or expose it as a shared web service. An allowlist, stronger deadline enforcement, retention, charts, and notifications remain future work.

## DocumentFlow

**Description / problem:** Prepare PDFs while keeping source documents unchanged and making page selection explicit.

**Solution:** Validate input PDFs and 1-based page ranges, construct the result in memory, and exclusively create a new output file. Output paths that already exist are rejected. Encrypted inputs are rejected.

```sh
python -m projects.documentflow info first.pdf
python -m projects.documentflow merge combined.pdf first.pdf second.pdf
python -m projects.documentflow extract combined.pdf selected.pdf --pages 1,3-5
python -m projects.documentflow rotate selected.pdf rotated.pdf --degrees 90
```

Supply your own small, nonsensitive input PDFs. Tests generate their own PDFs automatically. Extraction follows the specified order; rotation applies to every output page. To rotate only selected pages through code, call `process([input], output, pages='2', rotation=90)`; this exports only those selected pages.

This prototype is not a signature-preserving editor, form-preservation tool, OCR engine, or compression utility. It rebuilds page content and does not guarantee preservation of document-level metadata, bookmarks, forms, or signatures. Modifying a signed document can invalidate signatures. Large files consume memory; there are no resource quotas. A disk write failure may leave a partial new output, but existing inputs are never overwritten. Review the exported PDF before use.

PDF operations use [pypdf's documented page APIs](https://pypdf.readthedocs.io/en/latest/user/cropping-and-transforming.html).

## Design and tests

`common.py` centralizes database transactions, timestamp parsing, and CLI error formatting. Business logic is callable without argparse, so tests can exercise transactions and failure cases directly. SQL values are parameterized. Each application normally uses its own local database. Do not place the databases on a network filesystem or share them with untrusted users.

```sh
python -m unittest discover -s tests -v
```

The suite has 17 tests and was run successfully on Python 3.12 with pypdf 6.10.0. It includes actual simultaneous database connections, actual local HTTP requests and a timeout, real generated PDF files, and subprocess CLI checks. It does not establish production readiness, performance limits, or cross-platform certification.
