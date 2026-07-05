# Stella — the AI receptionist that never clocks out

Stella answers a business's phone line 24/7 — booking appointments, taking structured intake, routing calls, and escalating to a human — using a natural, speech-to-speech voice agent. One engine, config-driven, serves every business vertical: no code branches per business type.

> Working name: **Stella** 

---

## Table of contents

- [What this is](#what-this-is)
- [How it works, in one paragraph](#how-it-works-in-one-paragraph)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Repository structure](#repository-structure)
- [Getting started](#getting-started)
- [Configuring a business](#configuring-a-business)
- [Vertical templates](#vertical-templates)
- [Calendar integration](#calendar-integration)
- [Structured intake](#structured-intake)
- [DTMF / keypad handling](#dtmf--keypad-handling)
- [Notifications](#notifications)
- [Recording, transcripts & retention](#recording-transcripts--retention)
- [Safety nets](#safety-nets)
- [Secrets & environment variables](#secrets--environment-variables)
- [Onboarding a new business](#onboarding-a-new-business)
- [Testing a business before go-live](#testing-a-business-before-go-live)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Compliance notes](#compliance-notes)
- [Contributing](#contributing)
- [License](#license)

---

## What this is

Small businesses — clinics, salons, grocery stores, general offices — lose customers to missed calls, after-hours calls, and no-shows. A full-time receptionist is expensive; a bad answering service sounds robotic and loses trust in the first ten seconds.

Stella is a phone-based voice agent that:

- Answers inbound calls within 1–2 rings with a business-specific greeting
- Understands what the caller wants (book, reschedule, cancel, ask a question, or talk to a person)
- Checks a real calendar and books/confirms appointments — where the business has appointments at all
- Runs structured intake for non-appointment info (new-patient forms, special orders, new-client details, warranty claims)
- Routes calls to named departments or takes a message with callback details
- Escalates to a human on request or after repeated confusion, instead of looping or hanging up
- Records calls and generates transcripts, with configurable retention
- Sends outcomes wherever the business already works — email, webhook, or a local file record

**The core design principle:** what differs between a clinic and a grocery store is entirely *configuration* — hours, routing, whether appointment booking is even relevant, what structured intake looks like. It is never code. A new business, even a new vertical, should be onboardable by filling out a YAML file, not by an engineer writing new logic.

---

## How it works, in one paragraph

A call comes in over SIP and lands in a LiveKit room. A single job-runner picks it up and hands it to one `Receptionist` agent, whose system prompt is generated at call time from that business's config file. The agent talks to the caller using OpenAI's Realtime API (speech-to-speech, no separate STT/TTS/LLM hop), and has a fixed set of tools available — check availability, book an appointment, transfer the call, take a message, record an intake answer, look up a FAQ, end the call, and so on. Whether a given tool is *useful* on a given call depends entirely on that business's config (e.g. a grocery store's config has no calendar block, so booking tools are simply irrelevant to its prompt). When the call ends, outcomes are written to whichever notification channels that business has enabled.

---

## Architecture

```
                         ┌─────────────────────┐
  Inbound call  ──SIP──▶ │   LiveKit SIP trunk  │
                         └──────────┬───────────┘
                                    │
                         ┌──────────▼───────────┐
                         │  livekit-agents job   │
                         │  runner (@server.rtc_ │
                         │  session: handle_call)│
                         └──────────┬───────────┘
                                    │  loads config for this business
                         ┌──────────▼───────────┐
                         │ config/businesses/    │
                         │   <slug>.yaml         │ (pydantic-validated)
                         └──────────┬───────────┘
                                    │  build_system_prompt()
                         ┌──────────▼───────────┐
                         │   Receptionist Agent  │
                         │  (OpenAI Realtime,    │
                         │   speech-to-speech)   │
                         └───┬───────┬───────┬───┘
                             │       │       │
                 ┌───────────┘   ┌───┘   ┌───┘
                 ▼               ▼       ▼
        booking/client.py   intakes/   dtmf handling
        booking/availability.py  (config-defined
        (Google Calendar)         case types & Qs)
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
         recordings / transcripts   notifications
         (local or S3, per-        (file / email /
          business retention)       webhook — any combo)
```

Every inbound call, regardless of business or vertical, flows through the same handler. The only thing that changes call-to-call is which config file gets loaded.

---

## Tech stack

| Layer | Technology |
|---|---|
| Telephony / media | [LiveKit](https://livekit.io) (SIP trunking into LiveKit rooms via `livekit-agents`) |
| Voice model | OpenAI Realtime (`gpt-realtime`), speech-to-speech |
| Calendar | Google Calendar (OAuth or service account) |
| Backend runtime | Python — `livekit-agents`, `pydantic`, `pyyaml` |
| Config | Per-business YAML, `pydantic`-validated, fails fast on bad config at startup |
| Storage | Local disk or S3 for recordings/transcripts; local files, SMTP/Resend email, or webhooks for notifications |

There is currently **no database** — see [Repository structure](#repository-structure) and [Known limitations](#known-limitations).

---

## Repository structure

```
.
├── config/
│   └── businesses/
│       ├── clinic_example.yaml
│       ├── salon_example.yaml
│       ├── grocery_example.yaml
│       ├── general_office_example.yaml
│       └── <your-business-slug>.yaml
├── secrets/
│   └── <your-business-slug>/       # OAuth tokens, credential files (gitignored)
├── booking/
│   ├── client.py                   # Google Calendar client
│   └── availability.py             # availability-checking logic
├── intakes/                        # generic, config-defined Q&A engine
├── prompts.py                      # build_system_prompt(): config -> system prompt
├── agent.py                        # Receptionist Agent + tool surface
├── server.py                       # @server.rtc_session handler (handle_call)
├── VERTICAL_ONBOARDING.md          # step-by-step guide to onboarding a new business
└── README.md
```

> Adjust this tree to match your actual file layout if it's diverged — this reflects the architecture as described in the project's design docs.

---

## Getting started

### Prerequisites

- Python 3.10+
- A [LiveKit](https://livekit.io) project with SIP trunking configured
- An OpenAI API key with access to the Realtime API (or an OAuth-based login flow, if configured)
- A Google Cloud project with the Calendar API enabled (only needed for businesses that book appointments)

### Install

```bash
git clone <this-repo-url>
cd <repo-name>
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure environment variables

Copy the example env file and fill in your own values:

```bash
cp .env.example .env
```

See [Secrets & environment variables](#secrets--environment-variables) for what's required.

### Run a business locally

```bash
python server.py --business config/businesses/salon_example.yaml
```

Or, if config is selected by environment variable instead of a flag:

```bash
export BUSINESS_CONFIG=config/businesses/salon_example.yaml
python server.py
```

Point a LiveKit SIP trunk (or a sandbox test number) at this instance to place a test call.

---

## Configuring a business

Every business is a single YAML file under `config/businesses/`. At minimum, expect sections like:

```yaml
business:
  slug: bloom-and-co-salon
  name: "Bloom & Co Salon"
  timezone: America/Chicago
  greeting: "Thanks for calling Bloom & Co, this is Stella — how can I help?"
  hours:
    monday: "09:00-18:00"
    tuesday: "09:00-18:00"
    # ...

voice:
  model: gpt-realtime
  voice_id: <voice-id>

calendar:                     # omit entirely for businesses without appointments
  provider: google
  calendar_id: <calendar-id>
  appointment_duration_minutes: 45

intake:                       # omit if this business has no structured intake
  case_types:
    - name: new_client
      questions:
        - id: full_name
          prompt: "Can I get your full name?"
          required: true

dtmf:                         # optional, for keypad-driven menus / digit-only answers
  departments:
    "1": front_desk
    "2": billing

notifications:
  channels:
    - type: email
      to: owner@example.com
    - type: webhook
      url: "${BOOKING_WEBHOOK_URL}"

recording:
  enabled: true
  consent_preamble: true
  retention_days:
    recordings: 30
    transcripts: 90
    messages: 180
```

Config is validated with `pydantic` at startup — a missing file, bad cross-reference, or invalid field fails immediately rather than mid-call. `${VAR}` syntax in any field pulls from environment variables, so secrets are never committed to the YAML itself.

---

## Vertical templates

Four ready-to-use templates live in `config/businesses/`:

| Template | Calendar | Intake | Notes |
|---|---|---|---|
| `clinic_example.yaml` | Yes | Yes (new-patient forms) | Shortened retention by default; PHI-aware |
| `salon_example.yaml` | Yes | No | Fixed appointment-slot length (see limitations) |
| `grocery_example.yaml` | No | Yes (special orders) | No booking — intake and routing only |
| `general_office_example.yaml` | No | No | Department routing + message-taking only |

Start from the closest template and fill in your business's specifics — see [Onboarding a new business](#onboarding-a-new-business).

---

## Calendar integration

- Google Calendar only, today — authenticated via OAuth or a service account, configured per business
- Availability checks and bookings go through `booking/client.py` and `booking/availability.py`
- Entirely optional: omit the `calendar:` block for verticals that don't take appointments (e.g. a grocery store)
- Appointment slots are a **fixed length per business** (`appointment_duration_minutes`) — see [Known limitations](#known-limitations)

---

## Structured intake

The `intakes/` module is a generic, config-defined Q&A engine. Any business defines its own "case types" and questions in YAML — no code changes required. Supports:

- Voice or DTMF-keypad answers
- Required / critical / read-back flags per question
- Partial-answer persistence, so a dropped call doesn't lose data the caller already gave

This is the same mechanism whether the intake is a new-patient form, a special grocery order, or a new-client detail sheet.

---

## DTMF / keypad handling

Keypad input is handled **deterministically**, not by the LLM — this matters for reliability on things like department shortcuts and digit-only answers (phone numbers, IDs). Defined per business under the `dtmf:` config block.

---

## Notifications

Pluggable, and any combination can be enabled at once:

| Channel | Use case |
|---|---|
| `file` | Local disk, zero setup — good default for early testing |
| `email` | SMTP or Resend — a summary lands in an inbox, no login needed |
| `webhook` | POST into an existing ticketing system, CRM, or order-management tool |

---

## Recording, transcripts & retention

- Recording is optional per business; when enabled, callers hear a spoken consent preamble (for two-party-consent jurisdictions)
- Storage is local disk or S3
- Retention is set **independently** for recordings, transcripts, and messages — shorten these for businesses handling sensitive data (health, legal, financial)

---

## Safety nets

Built into the call handler regardless of business or vertical:

- **Silence timeout** — re-prompts once, then offers a human transfer instead of waiting indefinitely
- **Max call duration** — a hard cap with a graceful handoff before it's reached
- **Unproductive-turn detection** — ends the call gracefully if the agent is visibly stuck in a loop
- **Automatic error recovery** — transient Realtime API errors (rate limits, rejected responses) are retried so the caller isn't left in dead air

---

## Secrets & environment variables

Per-business secrets (OAuth tokens, credential files) live in `secrets/<slug>/` and should **never** be committed — add this directory to `.gitignore` if it isn't already.

Typical `.env` values:

```
OPENAI_API_KEY=
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
GOOGLE_CALENDAR_CREDENTIALS_PATH=
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=
BOOKING_WEBHOOK_URL=
```

Any of these can also be referenced from inside a business's YAML config using `${VAR}` interpolation.

---

## Onboarding a new business

Full steps live in `VERTICAL_ONBOARDING.md`; the short version:

1. Copy the closest template from `config/businesses/`
2. Fill in identity, hours, routing, and FAQs
3. Add calendar and/or intake blocks if relevant to this business
4. Run `booking setup` and `voice setup` (or your project's equivalent init commands)
5. Test end-to-end on a sandbox SIP trunk before pointing a real number at it

**Done criteria for a new business:** a caller can complete that vertical's core task (booking, special order, intake, routing) entirely by voice with no human involvement in most calls; every outcome is logged; failed calls escalate gracefully instead of dead-ending.

---

## Testing a business before go-live

Before a real number goes live, test on a sandbox line for:

- Interruptions / barge-in (assistant must stop talking immediately)
- Background noise and varied accents
- Silence and dead air
- Multiple requests in a single call
- Caller changing their mind mid-flow
- Vertical-specific edge cases (e.g. a grocery caller asking about live inventory — the system should correctly say it can't help with that, not guess)

Recommended rollout: launch with 1–2 real businesses per target vertical, off-hours only at first, and monitor outcomes before expanding to full coverage.

---

## Known limitations

- **No reschedule/cancel tools yet.** The current tool surface only has `check_availability` and `book_appointment` — there's no `reschedule_appointment` or `cancel_appointment` tool. Today, a caller wanting to reschedule or cancel goes through `take_message` for a human to handle. This is the highest-priority gap before rolling out to verticals where it's common (clinics, salons).
- **Fixed appointment-slot length per business.** There's no per-service duration — a salon's 15-minute trim and 3-hour color both book the same slot length unless staff manually adjust.
- **No database.** Everything persists to local (or S3) files per business — recordings, transcripts, messages, intake submissions. This is genuinely vertical-agnostic and needs zero migrations to onboard a new vertical, but doesn't scale past "grep the file store" once you have many businesses. See [Roadmap](#roadmap).
- **Google Calendar only.** No other calendar providers are supported today.
- **Out of scope for v1:** multi-provider scheduling (matching a specific doctor + room + equipment), insurance verification, outbound sales calls, live inventory/price lookups.

---

## Roadmap

- [ ] `reschedule_appointment` and `cancel_appointment` tools
- [ ] Real database (see schema sketch below) once file-based storage stops scaling, or once a business-owner dashboard is prioritized
- [ ] Business-owner dashboard (today's bookings, call log, transcript + audio playback, settings)
- [ ] Outbound reminder calls
- [ ] Per-service appointment durations
- [ ] Additional calendar providers
- [ ] Payment/deposit collection on call
- [ ] CRM/EHR integrations beyond generic webhooks
- [ ] Cross-business analytics on call outcomes

<details>
<summary>v2 database schema sketch</summary>

```
businesses(id, name, phone_number, timezone, business_hours, greeting_script,
           calendar_provider, calendar_credentials, created_at)
staff_users(id, business_id FK, email, role, created_at)
services(id, business_id FK, name, duration_minutes, price)
appointments(id, business_id FK, caller_id FK, service_id FK, start_time, end_time,
             status, source, created_at)
callers(id, business_id FK, phone_number, name, created_at)
call_logs(id, business_id FK, caller_id FK, appointment_id FK, call_sid, transcript,
          audio_url, outcome, duration_seconds, created_at)
```

Row-level security would scope `staff_users` to their own `business_id`; callers are never authenticated and are matched by phone number.

</details>

---

## Compliance notes

Businesses handling PHI or other sensitive data (clinics, legal/financial offices) need a documented data-handling review before onboarding real patient/client data — confirm agreements with OpenAI, the email provider, and the storage provider, and shorten retention accordingly (see the clinic template). This project does not itself constitute a compliance certification of any kind.

---

## Contributing

Issues and PRs welcome. If you're adding a new vertical, prefer adding a config template over adding vertical-specific code — that's the whole point of the architecture. If you find yourself writing `if vertical == "clinic"` anywhere outside config loading, that's a sign the change belongs in a YAML template instead.

---

