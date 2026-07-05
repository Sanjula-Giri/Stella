# Stella — AI Phone Receptionist (Prototype Scaffold)

This is a from-scratch starter implementation of the architecture described in
`ai-receptionist-game-plan.md`: one vertical-agnostic conversation engine,
config-driven per business, built on LiveKit + OpenAI Realtime.

Per the plan's own "suggested build order," this scaffold is set up to be
tested with a **fake calendar first** — validate voice latency and
conversation flow before wiring up real Google Calendar / real telephony.

## What's here

```
stella-prototype/
├── config/
│   ├── schema.py                  # pydantic models that validate business YAML
│   └── businesses/
│       └── clinic_example.yaml    # one filled-out example business config
├── app/
│   ├── server.py                  # LiveKit entrypoint (handle_call)
│   ├── agent.py                   # Receptionist Agent + tool surface
│   ├── prompts.py                 # build_system_prompt(): config -> system prompt
│   ├── booking/
│   │   ├── client.py              # Google Calendar client (real)
│   │   ├── availability.py        # slot-finding logic
│   │   └── fake_calendar.py       # in-memory calendar for prototyping w/o Google
│   └── intakes/
│       └── engine.py              # generic config-driven Q&A engine
├── docs/
│   ├── CONVERSATION_DESIGN.md     # the "7th document" — the actual call script
│   └── VERTICAL_ONBOARDING.md     # how to onboard a new business
├── requirements.txt
└── .env.example
```

## Running the prototype (fake calendar mode)

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in `OPENAI_API_KEY` and
   `LIVEKIT_*` values. You do **not** need Google Calendar credentials yet —
   leave `calendar.provider: fake` in the business config and it'll use
   `booking/fake_calendar.py` instead.
3. `python -m app.server --business config/businesses/clinic_example.yaml`
4. Connect a LiveKit test room (or the LiveKit CLI's SIP simulator) to place
   a test call and validate turn-taking/latency before touching real
   telephony or a real calendar.

## What's intentionally stubbed

This scaffold implements the *shape* of every component in the TRD, but two
things are deliberately left as clearly-marked stubs since they need your
own credentials/decisions to be real:

- **Google Calendar auth** in `booking/client.py` — OAuth flow is stubbed;
  swap in `google-auth`/`google-api-python-client` calls once you've decided
  OAuth vs. service account.
- **Notification channels** (email/webhook) — the interface exists in
  `agent.py`'s `take_message`/`finalize_intake` tools, but the actual
  SMTP/webhook senders are left as `TODO` so you can plug in your own
  provider (SMTP, Resend, etc.) without guessing your credentials.

Everything else — the agent's tool surface, config-driven system prompt,
fake calendar, and intake engine — is runnable as-is.
