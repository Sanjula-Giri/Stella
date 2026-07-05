# "Stella" — AI Phone Receptionist
## Full Game Plan (6 Documents + Voice-Specific Build Roadmap)

A natural-sounding phone assistant that books, confirms, and reschedules appointments for clinics, salons, and small offices — 24/7.

> **Update:** this has moved from concept to a real, working codebase (LiveKit + OpenAI Realtime + Google Calendar, config-driven per business). The docs below have been revised to match that architecture and to be genuinely vertical-agnostic — the same engine now serves clinics, salons, grocery stores, and general offices through per-business YAML config, not code branches. See `VERTICAL_ONBOARDING.md` and the four ready-to-use templates in `config/businesses/` (clinic, salon, grocery store, general office).

---

## Why voice AI needs this framework *more* than a typical app

A web app's bugs are visible and patchable. A phone call is a live, one-shot conversation — if the assistant mishears a date, talks over a caller, or loops on "sorry, can you repeat that," the business loses a customer in real time and you may not even know it happened. So before writing a single prompt or line of code, lock down the six documents below. For voice products, three extra concerns sit on top of the standard web-app framework: **latency**, **conversation design** (not just navigation), and **telephony/compliance**. Those are folded in throughout.

---

## 01 — PRD (Product Requirements Document)

| Field | Content |
|---|---|
| **App Name** | e.g. Jarvis (placeholder — needs a real name) |
| **Tagline** | "The receptionist that never clocks out." |
| **Problem** | Small businesses of any kind — clinics, salons, grocery stores, offices, repair shops — lose calls to missed calls, after-hours calls, and no-shows. Hiring a full-time receptionist is expensive; a bad answering service feels robotic and loses trust. |
| **Target User** | Two personas: (1) **Business owner/office manager**, of *any* vertical — non-technical, time-poor, wants fewer missed calls and less admin, regardless of whether their business books appointments, takes orders, or just routes calls. (2) **End caller** — a customer/patient/client who wants a fast, natural answer without navigating a phone tree. |
| **Vertical-agnostic design principle** | The product must not be built around one business type. What differs between a clinic and a grocery store is entirely **configuration** (hours, routing, whether appointment booking is even relevant, what structured intake looks like) — never code. A new vertical should be onboardable by filling out a config file, not by an engineer writing new logic. |
| **Core Features (Must Have)** | Inbound call answering with natural voice · Configurable per-business persona, hours, and FAQs · Call routing/transfer to named departments · Take a message with callback details · (Optional, per business) Book/check/cancel appointments against a real calendar · (Optional, per business) Structured phone intake for non-appointment info (new-patient forms, special orders, new-client details, warranty claims) · Call recording + transcript with configurable retention · Message/booking notifications via email and/or webhook into existing internal systems · Escalate to human on request or confusion |
| **Nice to Have (v2)** | Outbound reminder calls · A dashboard for business owners (currently file/email-based, no UI) · Payment/deposit collection on call · CRM/EHR integrations beyond generic webhooks · Analytics on call outcomes across many businesses |
| **Out of Scope (v1)** | Complex multi-provider scheduling (matching a specific doctor + room + equipment) · Insurance verification · Outbound sales/marketing calls · Live inventory/price lookups (e.g. for grocery) |
| **User Stories** | As a *caller to any kind of business*, I want to talk naturally instead of navigating a phone tree or website. As an *owner in any vertical*, I want to onboard my business by filling out one config file, not by requesting a custom build. As a *caller*, I want to be transferred to a human if the AI can't help, so I'm never stuck. |
| **Success Metrics** | % of inbound calls resolved without human escalation · Average call handle time · Time to onboard a new business (config-to-live) · Booking/intake conversion rate where applicable · Business owner retention after 30/60/90 days, tracked across verticals to catch vertical-specific gaps |

---

## 02 — TRD (Technical Requirements Document)

**Status: this is no longer speculative — it reflects the actual codebase.** The original draft of this doc proposed Twilio + Vapi/Retell as a starting stack; the real build instead sits on LiveKit + OpenAI Realtime, which is documented here as the source of truth.

| Field | Content |
|---|---|
| **Telephony/media layer** | LiveKit (SIP trunking into LiveKit rooms, `livekit-agents` job-runner framework). One `@server.rtc_session` handler (`handle_call`) processes every inbound call regardless of vertical. |
| **Voice model** | OpenAI Realtime (`gpt-realtime`), speech-to-speech — no separate STT/TTS/LLM hop; latency and turn-taking are handled by the Realtime API directly. Voice ID, model, and auth (API key, or OAuth via Codex login) are all per-business config. |
| **Conversation engine** | A single `Receptionist` `Agent` class with a fixed tool surface (`check_availability`, `book_appointment`, `transfer_call`, `take_message`, `record_intake_answer`, `finalize_intake`, `await_keypad_entry`, `send_info_packet`, `get_business_hours`, `lookup_faq`, `end_call`). The **system prompt is generated per business** from config (`prompts.py: build_system_prompt`) — this is the actual mechanism that makes one engine serve every vertical. |
| **Calendar integration** | Google Calendar only today (OAuth or service-account auth), abstracted behind `booking/client.py` + `booking/availability.py`. Calendar is entirely optional per business — omit the `calendar:` config block for verticals that don't book appointments (e.g. grocery stores). |
| **Structured intake** | A generic, config-defined Q&A engine (`intakes/`) — any vertical defines its own "case types" and questions in YAML (new-patient forms, special orders, new-client details) with no code changes. Supports voice or DTMF-keypad answers, required/critical/read-back flags, and partial-answer persistence so a dropped call doesn't lose captured data. |
| **DTMF / keypad menus** | Deterministic (not LLM-routed) keypad handling for department shortcuts and digit-only intake answers (phone numbers, SSNs) — config-defined per business (`dtmf:` block). |
| **Messaging/notifications** | Pluggable message channels per business: `file` (local disk, zero setup), `email` (SMTP or Resend), `webhook` (POST into an existing internal system — ticketing, CRM, order management). Any combination can be enabled simultaneously. |
| **Recording & transcripts** | Optional per business, local or S3 storage, with a spoken consent preamble for two-party-consent jurisdictions. Retention (days) is independently configurable for recordings, transcripts, and messages — critical for verticals handling sensitive data (health, legal, financial). |
| **Backend runtime** | Python (`livekit-agents`, `pydantic` for config validation, `pyyaml`). Config is `pydantic`-validated YAML per business (`config/businesses/<slug>.yaml`), loaded by job metadata or an env var at call time — fails fast at startup on bad config (missing files, invalid cross-references) rather than failing mid-call. |
| **Environment/secrets** | Per-business `secrets/<slug>/` directory holds OAuth tokens and credential files; `${VAR}` interpolation in YAML pulls sensitive values (SMTP passwords, webhook tokens) from environment variables rather than committing them to config. |
| **Safety nets already built** | Silence-timeout hangup, max-call-duration cap, "unproductive turn" detection (ends the call gracefully if the agent is visibly stuck), automatic recovery from transient Realtime API errors (rate limits, rejected responses) so the caller isn't left in dead air. |
| **Compliance flag** | Verticals handling PHI or other sensitive data (clinics, legal/financial offices) need a documented data-handling review — confirm agreements with OpenAI, the email provider, and storage provider before onboarding real patient/client data; shorten retention accordingly (see the clinic template). |
| **Known v1 limitation** | Appointment slots are fixed-length per business (`appointment_duration_minutes`) — there's no per-service duration (e.g. a salon's 15-minute trim vs. 3-hour color both book the same slot length unless staff manually adjust). Documented as a known constraint in the salon template rather than solved in v1. |

---

## 03 — App Flow (here: **Call Flow + Dashboard Flow**)

For a voice product, "app flow" splits into two: the **conversation flow** (what happens on the phone) and the **dashboard flow** (what the business owner sees). The conversation flow is the one most teams skip — don't.

### Conversation Flow (the actual product)
| Stage | Detail |
|---|---|
| **Call answered** | Assistant answers within 1–2 rings with a branded greeting: "Thanks for calling [Business], this is [Assistant Name] — how can I help?" |
| **Intent detection** | New booking / Confirm existing / Reschedule / Cancel / Speak to a human / Other |
| **New booking flow** | Ask service type → ask preferred date/time → check real-time availability → offer 2–3 alternatives if unavailable → confirm details back to caller → book → send SMS/email confirmation |
| **Reschedule/cancel flow** | Identify caller (phone number match or name+DOB depending on vertical) → pull up existing appointment → confirm which one if multiple → make the change → confirm back |
| **Escalation triggers** | Caller asks for a human explicitly · 2+ failed recognition attempts in a row · Request outside scope (e.g. medical question, pricing dispute) → warm transfer to a real line, or take a voicemail with callback promise |
| **Call end** | Recap what was booked/changed, confirm caller has the SMS/email, polite sign-off |
| **Edge cases** | Silence/no response → re-prompt once, then offer human transfer · Background noise / unclear speech → ask to repeat, don't guess on critical details like time · Caller interrupts mid-sentence (barge-in) → assistant must stop talking immediately, not talk over them · Multiple appointments in one call · Caller changes their mind mid-flow |

### Dashboard Flow (secondary, for business owner)
| Field | Detail |
|---|---|
| **Pages** | `/login`, `/dashboard` (today's bookings + call log), `/calendar`, `/settings` (business hours, greeting script, calendar connection), `/calls/:id` (transcript + audio playback) |
| **First screen** | Dashboard showing today's bookings and recent calls |
| **Auth flow** | Login → dashboard (no onboarding wizard needed for v1 beyond connecting a calendar) |
| **Empty states** | "No calls yet — forward your business line to [number] to get started" |
| **Redirects** | After login → `/dashboard`; after logout → `/login` |

---

## 04 — UI/UX Design Brief (Dashboard only — the "product" itself has no visual UI)

| Field | Content |
|---|---|
| **Aesthetic** | Clean, trustworthy, low-friction — think Calendly meets a CRM. Business owners are often non-technical; avoid dense data screens. |
| **Primary Color** | e.g. #2563EB (trust-signaling blue) |
| **Background** | #FFFFFF light mode primary (this audience skews toward light mode) |
| **Text Color** | #1A1A1A |
| **Accent/CTA** | #16A34A (green, for "booked" states) |
| **Font** | Inter |
| **Border Radius** | 8–12px, soft and approachable |
| **Component style** | Card-based layout for call logs and bookings, subtle shadows, no heavy chrome |
| **Reference Apps** | Calendly, Squarespace Scheduling, Intercom's dashboard |
| **Mobile** | Must be usable on mobile — office managers check bookings from their phone constantly |
| **Accessibility** | High contrast on call transcripts, adjustable font size (this audience includes older salon/clinic owners) |

**Important non-visual UX note:** the *voice* is the real UI here. Invest early in scripting the assistant's tone — warm but efficient, never over-apologetic, confirms details back explicitly ("So that's Tuesday the 8th at 2pm for a haircut — is that right?") to build caller trust.

---

## 05 — Backend Schema

**Current v1 reality:** the actual codebase doesn't use a database at all — each business persists to its own local (or S3) files: recordings, JSON/markdown transcripts, message files, and intake submissions, keyed by business slug. Notifications go out via email/webhook rather than being queried from a dashboard. This is genuinely vertical-agnostic (a grocery store's special-order file looks structurally the same as a clinic's intake file) and requires zero schema migrations to onboard a new vertical.

The schema below is the **v2 roadmap** — a real database becomes worth it once you have enough businesses that "grep the file store" stops scaling, or once a business-owner dashboard (see App Flow, Dashboard section) becomes a priority. It's written to be equally vertical-agnostic: nothing below assumes clinics or salons specifically.

| Table | Columns |
|---|---|
| **businesses** | id (uuid), name, phone_number (assigned Twilio number), timezone, business_hours (jsonb), greeting_script (text), calendar_provider, calendar_credentials (encrypted), created_at |
| **staff_users** | id, business_id (FK), email, role (owner/staff), created_at |
| **services** | id, business_id (FK), name, duration_minutes, price (nullable) |
| **appointments** | id, business_id (FK), caller_id (FK), service_id (FK), start_time, end_time, status (booked/confirmed/cancelled/rescheduled/no_show), source (ai_call/manual), created_at |
| **callers** | id, business_id (FK), phone_number, name (nullable — captured during call), created_at |
| **call_logs** | id, business_id (FK), caller_id (FK), appointment_id (nullable FK), call_sid (Twilio ref), transcript (text), audio_url, outcome (booked/rescheduled/escalated/abandoned), duration_seconds, created_at |
| **Relationships** | appointments.business_id → businesses.id · appointments.caller_id → callers.id · call_logs.appointment_id → appointments.id (nullable, not every call results in a booking) |
| **Auth Provider** | Supabase Auth for staff_users only; callers are never authenticated, matched by phone number |
| **Row Level Security** | staff_users can only read/write data where business_id matches their own business |
| **Sensitive Fields** | calendar_credentials encrypted at rest · call transcripts/audio treated as PHI if clinic vertical is in scope — encrypt and set retention/deletion policy accordingly |
| **File Storage** | Call recordings via Supabase Storage or Twilio's own recording storage — `/recordings/{business_id}/{call_sid}.mp3` |

---

## 06 — Implementation Plan (Voice-adapted)

**Status update:** Phases 1–7 below (the hard part — the live conversation engine, calendar integration, booking logic, confirm/reschedule/cancel flows, escalation, and notifications) are already built and are vertical-agnostic by design. What's left is genuinely a **rollout plan across verticals**, not a from-scratch build. The phase table is kept below for reference and for anyone extending the engine further (e.g. new calendar providers, a dashboard).

| Phase | Goal | Status |
|---|---|---|
| **Phase 1: Setup** | Provision telephony (LiveKit + SIP trunk), repo, env vars | ✅ Built |
| **Phase 2: Conversation Prototype** | Validate latency and voice quality with OpenAI Realtime | ✅ Built |
| **Phase 3: Calendar Integration** | Google Calendar availability + booking, optional per business | ✅ Built |
| **Phase 4: Database + Booking Logic** | Persist appointments/callers/logs — currently file-based per business (see Backend Schema) | ✅ Built (file-based) |
| **Phase 5: Confirm / Reschedule / Cancel flows** | Extend booking to existing-appointment lookups | ❌ **Gap found**: the current tool surface only has `check_availability` and `book_appointment` — there's no `reschedule_appointment` or `cancel_appointment` tool. Today a caller wanting to reschedule/cancel would have to go through `take_message` for a human to handle. Worth prioritizing before rollout to verticals where this is common (clinics, salons) — see note below. |
| **Phase 6: Escalation & Fallback** | Human transfer, voicemail fallback, silence/duration/unproductive-turn safety nets | ✅ Built |
| **Phase 7: Notifications** | Email/webhook confirmation per outcome | ✅ Built |
| **Phase 8 (new): Vertical Config Library** | Ready-made, validated YAML templates per vertical (clinic, salon, grocery, general office) so onboarding a new business type is a config copy, not an engineering task | ✅ Delivered — see `config/businesses/*_example.yaml` + `VERTICAL_ONBOARDING.md` |
| **Phase 9 (new): Per-Business Onboarding** | For each real business: copy the closest template, fill in identity/hours/routing/FAQs, run `booking setup` + `voice setup`, test on a sandbox SIP trunk | Repeatable per business — see onboarding steps in `VERTICAL_ONBOARDING.md` |
| **Phase 10: Testing** | Real phone call testing per vertical — test interruptions, background noise, accents, silence, multiple requests in one call, and vertical-specific edge cases (e.g. grocery callers asking about live inventory the system correctly can't answer) | Ongoing per new business |
| **Phase 11: Pilot Deploy** | Launch with 1–2 real businesses per target vertical, off-hours only first, monitor outcomes before going fully live | Repeat per vertical |
| **Phase 12: Compliance Review** | Required before onboarding any business handling PHI or other sensitive data (clinics, legal/financial offices) — confirm data agreements with every vendor in the pipeline | Per business, as needed |
| **Done Criteria (per new business)** | A caller can complete whatever that vertical's core task is (booking, special order, intake, routing) entirely by voice with no human involvement in most calls; every outcome is logged; failed calls escalate gracefully instead of dead-ending |

---

## The one thing not in the original framework: **Conversation Design Doc**

For a voice product specifically, consider a lightweight 7th artifact before coding: a **call script / decision tree** — the actual words the assistant says at each branch, including how it handles "I don't understand," interruptions, and escalation. This is the equivalent of wireframes for a voice product. Without it, you'll end up prompt-engineering live against real callers, which is expensive in trust and reputation.

---

### Suggested build order summary
1. PRD + TRD (decide vertical: clinics vs. salons — this changes compliance scope significantly)
2. Conversation script/decision tree (the "voice wireframe")
3. Prototype the raw voice pipeline with a fake calendar — validate latency/naturalness first
4. Real calendar integration + database
5. Dashboard last — it's the least risky part technically

Once these are drafted, paste them all at the start of your AI coding agent session and say: *"Here are my project documents — use these as the source of truth for everything you build."*
