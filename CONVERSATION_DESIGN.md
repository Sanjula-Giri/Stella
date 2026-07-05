# Conversation Design Doc — Stella (worked example: Riverside Family Clinic)

This is the "voice wireframe" the game plan calls for — the actual words the
assistant says at each branch, not just the abstract flow. Written against
`config/businesses/clinic_example.yaml`; copy this structure per business.

## Opening

> "Thanks for calling Riverside Family Clinic, this is Stella — how can I
> help you today?"

If recording is enabled, the consent line is delivered as part of the
system prompt before the greeting:

> "This call may be recorded for quality and record-keeping purposes."

## Intent routing (first caller turn)

| Caller says something like... | Route to |
|---|---|
| "I need to make an appointment" / "book" / "schedule" | New booking flow |
| "I need to change/move my appointment" | Reschedule flow |
| "I need to cancel" | Cancel flow |
| "Can I speak to someone" / "operator" / "human" | Immediate transfer |
| "I'm a new patient" | `start_intake("new_patient")` |
| Anything matching a configured FAQ | `lookup_faq` |
| Anything else / unclear | One clarifying question, then escalate if still unclear |

## New booking flow

1. **Ask service/reason**: "Sure — what's this appointment for?"
2. **Ask preferred day**: "What day works best for you?"
3. **Check availability** (`check_availability`): "Let me check... I have
   2, 2:30, or 3 o'clock — do any of those work?"
   - If none work: "I don't have anything else that day — would another
     day work, or should I have someone call you back?"
4. **Collect callback number** if not already known.
5. **Read back before booking** (critical detail — never skip):
   > "So that's Tuesday the 8th at 2pm — is that right?"
   - Only call `book_appointment` after an explicit "yes."
6. **Confirm and close**:
   > "You're all set for Tuesday the 8th at 2pm. You'll get a text
   > confirmation shortly. Anything else I can help with?"

## Reschedule flow

1. Identify caller: "Can I get the phone number your appointment is under?"
2. `reschedule_appointment` requires an existing match — if none found:
   > "I'm not finding an appointment under that number — can you double
   > check, or would you like me to take a message for the front desk?"
3. If multiple appointments exist, disambiguate: "I see two appointments —
   one on Thursday and one next Monday. Which one?"
4. New time follows the same check-availability + read-back pattern as
   booking.

## Cancel flow

Same identification step as reschedule, then:
> "Just to confirm — you'd like to cancel your appointment on [date] at
> [time]? ... Done, that's cancelled."

## Escalation triggers (say this, don't just silently transfer)

- Caller explicitly asks for a human:
  > "Of course — one moment while I connect you."
- Two failed recognition attempts in a row:
  > "I want to make sure I get this right — let me connect you with someone
  > who can help directly."
- Out-of-scope request (e.g. a medical question):
  > "That's something our nurse line should answer rather than me — would
  > you like me to transfer you, or take a message for a callback?"

## Edge cases — exact behavior

| Situation | Behavior |
|---|---|
| Silence after a question | Re-prompt once: "Sorry, are you still there?" Then offer transfer if still silent. |
| Unclear/noisy audio on a critical detail (date, time, phone number) | Never guess — ask to repeat: "Sorry, I didn't catch that — could you say the date again?" |
| Caller talks over the assistant (barge-in) | Assistant stops speaking immediately; does not finish its sentence. |
| Caller changes their mind mid-booking | Drop the in-progress booking state, re-ask from the current step forward — don't restart the whole call. |
| Caller has multiple requests in one call | Handle sequentially, confirm each individually, recap all of them at call end. |

## Call end (every call, regardless of outcome)

> "So to recap: [what was booked / changed / recorded]. [You'll get a text
> confirmation. / Someone will call you back.] Anything else before I let
> you go? ... Thanks for calling Riverside Family Clinic, have a great
> day."

## What to test once this is live on a real line

- Interruptions mid-sentence (barge-in) — does Stella actually stop talking?
- Background noise (car, other people talking) — does it ask to repeat
  rather than guessing?
- Regional accents — does recognition hold up on names/numbers?
- A caller who tries to jump between booking and an FAQ mid-flow.
- A caller who goes silent for 10+ seconds mid-booking.
