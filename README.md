# Hi, I'm Nathaniel Barnes

**IT professional building software focused on automation, reliable workflows, and security.**

I hold a bachelor's degree in Information Technology from Governors State University. My background includes university help desk support, laboratory equipment troubleshooting and calibration, and audiovisual and IT support. I enjoy turning practical troubleshooting problems into maintainable software.

## Technical background

- **Programming and scripting:** Python, PowerShell, and Bash.
- **Systems:** Windows, Windows Server, Linux, Active Directory, and hardware troubleshooting.
- **Networking:** TCP/IP, DNS, DHCP, and connectivity troubleshooting.
- **Cloud and security labs:** Azure, Microsoft Sentinel, Log Analytics, and KQL.

## Six implemented projects

**Status: runnable local CLI prototypes.** All six now have implementation code, documented commands, and automated tests. They share a small Python utility module. The web interfaces, authentication, and larger full-stack features remain [future roadmap items](ROADMAP.md).

| Project / source | Problem | Implemented solution | Stack |
| --- | --- | --- | --- |
| [HelpDeskFlow](projects/helpdeskflow.py) | Support requests lose ownership and history | Persistent tickets, assignments, comments, enforced status transitions, and audit events | Python, SQLite |
| [AssetTrack](projects/assettrack.py) | Devices get assigned twice or lose their assignment history | Unique asset tags, exclusive checkout, check-in, and assignment history | Python, SQLite |
| [LogSignal](projects/logsignal.py) | Repeated authentication failures are hard to spot manually | Validated JSONL ingestion, deduplication, rolling-window detection, and evidence per alert | Python |
| [AppointmentDesk](projects/appointmentdesk.py) | Concurrent bookings cause scheduling conflicts | Offset-aware booking, transactional overlap checks, rescheduling, and cancellation | Python, SQLite |
| [UptimePulse](projects/uptimepulse.py) | Endpoint failures go unnoticed | Repeated HTTP HEAD checks, latency recording, failure thresholds, incident recovery, and sample-based availability | Python, SQLite |
| [DocumentFlow](projects/documentflow.py) | Repetitive PDF preparation introduces page errors | Merge, extract/reorder, rotate, and inspect PDFs while refusing to overwrite files | Python, pypdf |

## Quick start

Requires Python 3.11 or newer. Clone or download this repository and open a terminal in its root directory.

```sh
git clone https://github.com/NAB-Tech-Services/NAB-Tech-Services.git
cd NAB-Tech-Services
python -m venv .venv
```

Activate on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```sh
source .venv/bin/activate
```

Then:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m projects.helpdeskflow create "Printer is offline"
python -m projects.helpdeskflow list
python -m projects.logsignal examples/auth.jsonl
```

The first five tools use Python's standard library; only DocumentFlow and the full test suite need pypdf. Every tool supports `--help` and emits JSON on success. Database paths default to the current directory; use `--db PATH` before the subcommand to select another file.

**[Read commands, examples, design decisions, and limitations →](projects/README.md)**

## Validation and scope

The automated suite covers ticket rollback, inventory constraints, concurrent booking conflicts, timezone offsets, log boundaries and deduplication, real local HTTP responses/timeouts, incident recovery, PDF ordering/rotation, malformed input, and CLI entry points. Tests use temporary databases, generated PDFs, synthetic logs, and a local HTTP server; no external service is needed.

These are educational prototypes for one trusted local operator. There is no login system, multi-user authorization, web UI, or production deployment. UptimePulse accepts operator-selected network targets and must not be exposed as a public URL-checking service. Use synthetic data for portfolio demonstrations.

## Professional interests

I'm interested in opportunities that combine software development, IT operations, and security. My goal is to turn practical troubleshooting experience into useful, maintainable applications.
