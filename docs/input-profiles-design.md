# Input profiles: mouse, touchpad and new devices

Decided by the team on 2026-11-26. This replaces the earlier plan of a
`pointer_type` (`mouse` / `touchpad`) label.

## Why there is no device label
Browsers report a touchpad as `pointerType = "mouse"` and offer no API that
names the input hardware. A calibration test on one laptop (2026-11-26) showed:

| Signal | Mouse | Touchpad | Useful? |
|---|---|---|---|
| Raw pointer events per second | ~118 | ~79 | Yes, but depends on the hardware |
| Coalesced events per `pointermove` | 1.79 | 1.19 | Yes, same caveat |
| Wheel steps | always `wheelDeltaY = -120`, `deltaY = 100` | fractional, not multiples of 120 | Yes, only when the user scrolls |
| Click press duration | 71–200 ms | 102–190 ms | No (overlaps) |
| Step size, pressure, width/height, `persistentDeviceId` | same | same | No |

Any fixed threshold would be a guess based on one laptop, would break with a
new mouse, and cannot be enforced on users. So the system identifies the
**user**, not the device.

## Design
1. **Device signals as features, not labels.** Extension 1.5.3 sends, per
   15-second window, in `mouse_features`: `pointer_event_rate_hz`,
   `coalesced_events_per_move`, `wheel_event_count`, `wheel_smooth_ratio`
   (share of wheel events that are not whole 120-unit notches; `null` when the
   user did not scroll). Older extensions send none of them; the API accepts
   both.
2. **Several profiles per user, found automatically.** Training clusters each
   user's pointer windows (for example K-Means or a Gaussian mixture on the
   behavioural features plus device signals). Each cluster is a profile with
   its own One-Class SVM. A new window is normal if it fits **any** of the
   user's profiles. A PC user usually ends up with one profile; a laptop user
   with two or three.
3. **Keyboard and pointer are scored together.** A pointer mismatch alone
   never locks a user out.

## New device or new mouse (gatekeeper)
When a new `device_id` appears, or pointer windows stop matching every profile,
the history gatekeeper compares the new windows with the user's history:

| Keyboard | Pointer | Meaning | Action |
|---|---|---|---|
| matches | matches | same user, known style | link the device to the existing profile |
| matches | does not match | probably the same user on a new device | step-up verification (password / OTP); if it passes, start a new profile on **probation** |
| does not match | does not match | possibly another person | alert / lock; no profile is created |

Probation: the new profile is built from the first ~40 windows (~10 minutes).
The keyboard must keep matching during probation; a keyboard mismatch cancels
the profile. A new profile is only ever created after a successful step-up, so
an attacker cannot enrol themselves as a "new device". A new laptop can also
change the keyboard model a little, which is why a new `device_id` with any
mismatch always triggers step-up.

## Limits
- At most **7 profiles** per user.
- A profile is removed only after it has not been used for **more than one
  year**. Nothing is removed earlier.
- If an 8th profile is needed before then, nothing is deleted automatically:
  a review request goes to the admin, who decides.
- All profiles stay in the database; recently used ones are kept in a server
  cache for fast scoring, and older ones are loaded on demand.

## Cost
Measured with scikit-learn 1.9 on 300 windows × 14 features: One-Class SVM
training 2–50 ms, scoring one window ~0.2 ms, model size ~9 KB. A user with 7
profiles × 2 models is about 130 KB; 1,000 users fit in roughly 100–130 MB.
Models run on the server, so the extension stays dependency-free.

## Where it lives in the code
- `extension/content.js` — collects the device signals.
- `src/api/routes.py`, `src/data/database.py` — optional fields / nullable
  columns (added to the existing table automatically).
- `src/data_pipeline/prepare_training_windows.py` — writes
  `live_mouse_device_signals.jsonl` (only windows from 1.5.3+), keyed by
  `subject_id` + `session_id` + `window_index`; the clean UB/live files keep
  the same structure.
