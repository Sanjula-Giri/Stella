# Onboarding a New Business or Vertical

This engine (LiveKit + OpenAI Realtime + Google Calendar) is **not**
vertical-specific — every business is a single YAML file. `business.type`
is a free-text label used only in the spoken system prompt ("You are the
receptionist for Riverside Family Dental, a **dental clinic**..."). Nothing
in the code branches on it. A clinic, a salon, a grocery store, and a law
office all run the identical `agent.py` — they differ only in which config
sections they turn on.

## The four starter templates

| Template | Calendar booking | Intake questions | DTMF menu | Notes |
|---|---|---|---|---|
| `clinic_example.yaml` | ✅ | ✅ (new patient) | — | Recording consent preamble on; retention shortened; HIPAA note at top |
| `salon_example.yaml` | ✅ (fixed 60-min slots) | — | ✅ | Keypad shortcut to front desk |
| `grocery_store_example.yaml` | — (not needed) | ✅ (special orders) | ✅ (dept. shortcuts) | Demonstrates the `webhook` message channel |
| `general_office_example.yaml` | — (commented example to add later) | ✅ (new client) | — | Shows how to layer in booking later without restructuring anything |

Every feature (calendar, intake, DTMF, recording, email, webhook) is
independently on/off per business — mix and match for whatever a given
vertical actually needs. All four templates above have been validated
against the live `BusinessConfig` Pydantic schema in this repo.

## Onboarding steps for a new business (any vertical)

1. **Pick the closest template** from the table above and copy it:
   ```
   cp config/businesses/salon_example.yaml config/businesses/<your-slug>.yaml
   ```
2. **Fill in the basics**: `business.name`, `business.type`, `timezone`,
   `greeting`, `personality`, `hours`, `routing`, `faqs`.
3. **Set up messaging.** At minimum, keep a `file` channel (works with zero
   external setup). Add an `email` channel + top-level `email:` block if you
   want message/booking emails — remember any channel of type `email` in
   `messages.channels` requires the top-level `email:` section too.
4. **(Optional) Enable calendar booking:**
   ```
   python -m receptionist.booking setup <your-slug>
   ```
   This walks through Google's OAuth flow and writes the token file the
   `calendar.auth.oauth_token_file` path points to. Config validation will
   fail fast at startup if that file doesn't exist yet — that's intentional.
5. **(Optional) Enable structured intake** for anything that isn't a
   calendar booking — new-patient forms, special orders, new-client
   consultations, warranty claims, whatever the vertical needs. Each
   question is just `key` + `prompt_en` + a few flags (`required`,
   `critical` for read-back, `input: dtmf` for phone/SSN-style digits).
6. **Set up voice auth:**
   ```
   python -m receptionist.voice setup <your-slug>
   ```
7. **Test locally** with a real or sandbox SIP trunk pointed at the agent
   before forwarding a live business line.
8. **Go live** — forward the business's phone number to the configured SIP
   trunk/agent.

## Deciding which features a new vertical needs

- **Books appointments with fixed-length slots?** (clinics, salons, repair
  shops, consultants) → enable `calendar`.
- **Takes structured info that isn't a booking?** (new-patient forms,
  special orders, new-client details, warranty/repair intake) → enable
  `intakes` with a case type per form.
- **Has multiple departments people ask for by name or want a keypad
  shortcut to?** → use `routing` (+ optionally `dtmf` for keypad
  shortcuts).
- **Needs calls forwarded into an existing internal system** (ticketing,
  order management, CRM) → add a `webhook` message channel instead of, or
  alongside, `email`/`file`.
- **Handles sensitive personal data** (health, legal, financial) → turn on
  `recording.consent_preamble`, shorten `retention`, and confirm data
  handling agreements with every vendor in the pipeline (OpenAI, email
  provider, storage) before going live.

None of this requires touching `agent.py`, `config.py`, or `prompts.py` —
the whole point of the generic design is that vertical differences live
entirely in YAML.
