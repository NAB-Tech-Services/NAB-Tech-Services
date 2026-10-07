# Original web application roadmap

The following describes the **future full-stack targets**, not the capabilities of the current command-line prototypes. See README.md and projects/README.md for implemented features.

### 1. HelpDeskFlow — IT Support Ticket Management

**Suggested repository name:** `helpdeskflow`

**Description:** A web application where users submit support requests and technicians manage tickets from intake through resolution.

**Problem:** Requests spread across email and chat are difficult to prioritize, assign, and audit. Users have limited visibility into progress.

**Proposed solution:** Store tickets in a relational database, expose a documented API, and provide separate requester and technician views. Enforce allowed transitions between Open, In Progress, Resolved, and Closed. Record each assignment and status change in an audit history.

**Core features:** Ticket creation, categories, priorities, technician assignment, comments, search, status filtering, and resolution notes.

**Engineering design:** Model users, tickets, comments, and ticket events separately. Validate requests on the server. Enforce authorization on every API operation so requesters can access only their own tickets and technicians receive explicitly assigned permissions.

**Completion criteria:** Demonstrate the full ticket lifecycle using synthetic users; reject unauthorized ticket access and invalid transitions; verify that audit entries persist; document API examples and local setup.

**Skills demonstrated:** API design, relational modeling, authentication, authorization, and workflow testing.

### 2. AssetTrack — IT Asset Inventory

**Suggested repository name:** `assettrack`

**Description:** An inventory application for tracking computers, monitors, printers, and other IT equipment.

**Problem:** Spreadsheet inventories become inconsistent when equipment changes hands or moves between locations.

**Proposed solution:** Give every asset a unique identifier and record assignment and lifecycle events. Provide searchable records and controlled CSV imports so inventory stays consistent as devices move through service, repair, and retirement.

**Core features:** Asset registration, employee assignments, location tracking, warranty dates, maintenance records, search, and CSV import/export.

**Engineering design:** Separate assets, locations, assignments, and maintenance events. Enforce unique asset tags. Use database transactions when checking equipment in or out. Validate imports before committing records and report errors by row.

**Completion criteria:** Reject duplicate tags; prevent two simultaneous active assignments for one asset; preserve assignment history; validate malformed imports; demonstrate a complete asset lifecycle using fictional inventory.

**Skills demonstrated:** Database constraints, transactions, data validation, import pipelines, and business application design.

### 3. LogSignal — Security Log Analyzer

**Suggested repository name:** `logsignal`

**Description:** A tool that ingests synthetic authentication logs and presents rule-based alerts with supporting evidence.

**Problem:** Large log files make repeated login failures and unusual authentication patterns hard to identify manually.

**Proposed solution:** Parse a documented JSON Lines input format, normalize timestamps, and group events by account and source address. Flag configurable patterns, such as multiple failed logins within a rolling time window, and display the events that triggered each alert.

**Core features:** Log ingestion, schema validation, configurable thresholds, alert summaries, time filters, and CSV export.

**Engineering design:** Keep parsing, normalization, rule evaluation, and presentation in separate modules. Use stable event identifiers for deduplication. Define timestamp and window-boundary behavior explicitly. Treat detections as review signals rather than proof of an attack.

**Completion criteria:** Include synthetic positive and negative fixtures; test time-window boundaries, duplicate events, and malformed records; show why each alert fired; document false-positive scenarios and input limitations.

**Skills demonstrated:** Parsing, data pipelines, time-series reasoning, modular design, and security-focused software development.

### 4. AppointmentDesk — Service Scheduling Application

**Suggested repository name:** `appointmentdesk`

**Description:** A booking application for independent service providers, suitable for an IT consulting or notary appointment workflow.

**Problem:** Manual scheduling can cause overlapping appointments, missing service details, and timezone confusion.

**Proposed solution:** Let providers define availability and service duration, then let clients request valid time slots. Store timestamps consistently, display the selected timezone clearly, and protect booking creation against concurrent requests for overlapping slots.

**Core features:** Service selection, availability management, booking, rescheduling, cancellation, and an administrative calendar.

**Engineering design:** Model services, availability, and bookings separately. Perform overlap checks transactionally, backed by a database constraint where appropriate. Define cancellation rules and use minimal fictional client data in demonstrations. This schedules appointments only; it does not perform notarization or identity verification.

**Completion criteria:** Concurrent requests cannot double-book a slot; rescheduling respects availability; cancellation releases capacity; daylight-saving transitions are tested; client records are protected by authorization.

**Skills demonstrated:** Concurrency control, date/time handling, full-stack development, and domain modeling.

### 5. UptimePulse — Website and API Monitor

**Suggested repository name:** `uptimepulse`

**Description:** A monitoring application that measures endpoint availability and response time and records incidents.

**Problem:** Small teams may discover a failed website or API only after users report it.

**Proposed solution:** Run scheduled checks against administrator-approved endpoints. Record latency and response outcomes, open incidents after a configurable failure threshold, and close them after confirmed recovery. Display recent checks and incident history in a dashboard.

**Core features:** Endpoint configuration, periodic checks, response-time charts, incident tracking, and optional notifications.

**Engineering design:** Separate the scheduler from the dashboard API. Bound timeouts, response sizes, and concurrency. Restrict targets and validate redirects to avoid reaching unintended private or metadata endpoints. Keep uptime calculations explicit about gaps in monitoring data.

**Completion criteria:** Demonstrate healthy, slow, failing, and recovered endpoints with local fixtures; verify timeout behavior and incident deduplication; test target restrictions; document the availability calculation.

**Skills demonstrated:** Background jobs, fault handling, observability, defensive networking, and integration testing.

### 6. DocumentFlow — PDF Processing Utility

**Suggested repository name:** `documentflow`

**Description:** A local application for organizing PDFs through merge, split, rotation, and page inspection operations.

**Problem:** Repetitive document preparation consumes time and can introduce missing pages, incorrect page order, or orientation errors.

**Proposed solution:** Let users select documents, specify page order and operations, and export a new PDF while preserving original inputs. Provide page counts and a clear operation summary before export.

**Core features:** Merge files, extract page ranges, rotate selected pages, inspect page counts, and export processed documents.

**Engineering design:** Separate PDF operations from the interface. Validate page ranges and input limits. Handle encrypted or damaged PDFs with clear errors. Use temporary working files with cleanup. Warn that modifying digitally signed PDFs can invalidate signatures, and use synthetic documents for demonstrations.

**Completion criteria:** Verify output page order, counts, and rotation; reject invalid ranges; handle encrypted and malformed inputs predictably; confirm original files remain unchanged and temporary files are cleaned up.

**Skills demonstrated:** File processing, input validation, error handling, interface design, and artifact verification.

## Implementation milestones

For each project:

1. Define the minimum viable scope and create sample data.
2. Implement the core behavior and document architecture decisions.
3. Test the important failure cases and access boundaries.
4. Add reproducible setup instructions, screenshots, and an example workflow.
5. Update its status only when the implementation supports the claim.


