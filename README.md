# Baseline

A training app that decides what you should do **today** — from how recovered
you are, what you have actually been doing, and the kit you actually own.
Everything stays on your own device.

Most plans tell you what to do on a Tuesday, decided weeks ago, whether or not
you slept badly or played a match yesterday. This one decides each morning,
gives you one session, and tells you what it ruled out and why.

## How a day works

1. Open the app. It greets you and shows one number: **readiness**.
2. **Check in** — about a minute. Sleep, and four sliders for how you feel.
   The sliders start where you left them yesterday, so an unchanged day is
   barely any input at all. If you wear a tracker, whatever it reports is
   filled in for you.
3. You get **one session**. Name, duration, intensity. Nothing else competes
   with it on the screen.
4. Tap **Why this?** if you want the reasoning — what counted for it, and what
   was ruled out. Tap **Change today's plan** if you disagree; overriding is
   recorded and adapted to, not punished.
5. **Start session.** The screen becomes the workout: one exercise at a time,
   what you lifted last time, plus and minus buttons for reps and weight — no
   keyboard — and a rest timer that starts itself when you finish a set.
6. Played football instead? **Log activity** is three answers — what, how
   long, how hard — and feeds straight into tomorrow's recommendation.
   Anything not in the list, you can just type, and it suggests as you go.

## Finding your way around

Four sections along the bottom. Each one **opens with the thing it is for**,
and keeps everything else one tap away rather than on the same screen.

| | Opens with | One tap away |
|---|---|---|
| **Today** | Today's session, and one Start button | Why this · Change the plan · Readiness detail |
| **Train** | This week's targets, and which of the 8 progression weeks you are in | Workouts · Exercises · Warm-ups · History |
| **Activity** | Log an activity, then what you have done recently | All activity · Totals · your sport |
| **Progress** | How the week went, and the load chart | Strength · Tests · Physique · Patterns |

**Settings** is the gear in the top right, grouped as **Profile · Training ·
Wearables · Data · Appearance · Cycle · About**.

Wearable numbers and trends live behind the readiness row on Today, so if you
do not use a tracker you never see an empty chart. Nothing about cycle
tracking appears anywhere unless you switch it on.

Every screen has a back button, and the phone's own back gesture works too.

## What it does

- **One recommendation a day**, with its reasoning shown — including the
  options it rejected and the reason for each
- **Nothing is assumed.** No sport, no equipment, no goal, no wearable, no
  injuries — every one of those starts empty, and empty is a valid answer. The
  app never makes you undo a choice you did not make
- **Any wearable, or none.** WHOOP, Garmin, Oura, Fitbit, Apple Watch, Samsung,
  Polar, COROS, or nothing at all. It asks only for the numbers your device
  actually reports, and works from a short daily check-in without one
- **Built around your sport**, not a fixed template. 18 sports, each with its
  own warm-up, priorities and weekly targets — or none, which is also fine
- **Only exercises you can do.** 173 exercises tagged with the equipment they
  need; tick nothing and you still get a full bodyweight programme
- **Logs anything.** A match, a hike, a kickabout. Unplanned activity is not a
  missed workout — the engine adapts around it
- **Shows what you lifted last time**, under each exercise, while you are
  standing in front of it
- **Progression is earned, not scheduled.** Miss a fortnight and the plan waits
  rather than marching you into a peak week you have not worked for
- **Injuries persist.** Name an area and a date and it routes around the
  movements that load it until then, keeping everything else
- **It grades its own advice.** After enough days it will tell you whether
  following the recommendation actually went better for you — including when
  the honest answer is "no difference"
- Light or dark, following your system setting

## Setting up

Seven questions, and you can skip or leave empty any of them: your name, what
you are training for, your sport, your equipment, how often you train, your
tracker, and your age and measurements. The last three are explicitly optional
— the button says **Skip** rather than pretending you must answer.

If you close it half way through, it reopens where you left off.

## Your data

Everything you enter stays in **your own browser**, on the device you entered it
on. This repository hosts the application code and nothing else.

- No accounts, no server, no database, no analytics, no trackers
- Nothing is uploaded anywhere — there is no endpoint to upload to
- Wearable exports are parsed inside the browser and never leave the device
- Each browser on each device keeps a completely separate dataset
- Anyone opening the same link gets an empty copy of the app, not your data
- Moving data between devices is a manual backup file you export yourself

You can check this in ten seconds: open the app in a private browsing window.
You will get an empty app and the setup wizard.

**Never commit a wearable export or a backup file to this repository.** Anything
committed is permanent and recoverable from git history, and Pages sites are
public even when the repository is private.

## Install it

**iPhone/iPad (Safari):** open the URL → Share (□↑) → **Add to Home Screen**
**Android (Chrome):** menu → **Install app**
**Windows/macOS (Chrome/Edge):** install icon in the address bar
**macOS (Safari):** File → **Add to Dock**

On iPhone this matters more than it looks: left as an ordinary Safari tab, iOS
may clear the app's stored data after about a week of not opening it. Added to
the Home Screen it is treated as a real app and kept.

Installed versions share the same local data as the browser tab.

## Cycle tracking (optional)

Off unless you turn it on, in **Settings → Cycle**. Nothing cycle-related
appears anywhere in the app until you do.

What it does:

- One row on Today: *"Day 12 · Estimated follicular"*, and a short daily log —
  bleeding, how today feels, cramps, symptoms, a note. All optional, and it
  does not ask again for energy or soreness because the check-in already did.
- Period start dates are worked out from the days you mark as bleeding, so
  marking "bleeding today" is the only input a cycle needs.
- Phases are **estimates**, labelled as such, with a confidence. If your
  history is thin or your cycle length varies, it says *"phase estimate
  unavailable"* rather than guessing.

What it deliberately does **not** do:

- It has no rule saying a phase means train less. Nothing like *"luteal =
  reduce volume"* exists in the code.
- Cycle context changes your readiness score **only** once your own logs show
  a repeated association for one particular phase — at least two recorded
  cycles, a cycle regular enough for phases to mean anything, at least six
  logged days in that phase, and an effect too large to be noise. Until all of
  that holds, the effect is exactly zero and your recommendations are
  identical to having the feature off.
- When it does apply, it is capped at **5 points out of 100**, and only one
  phase can ever carry it.
- It can never lift a pain cap. Report moderate or significant pain and the
  session is reduced regardless of anything cycle-related.
- What you report about today outranks any estimate. *"Feeling strong"* raises
  the score even in a phase your history flags; *"significant discomfort"*
  lowers it in one it does not.
- It never estimates fertility or ovulation dates as fact, never infers
  pregnancy, and never diagnoses anything.

Anything the app observes is described as a correlation in your own logs. It
will say *"you have tended to report a harder time around this phase"* — never
that hormones are causing anything.

Privacy is the same as everything else, which is to say total: it is stored in
your browser on your device, it is never uploaded, and it is not in this
repository. A backup file lists **MENSTRUAL CYCLE DATA** in its header when it
contains any, so you know what you are sending if you ever send one.
**Settings → Cycle → Delete all cycle data** removes every entry and date and
keeps your training history.

## Back up

**Settings → Data → Backup** writes one file containing everything;
**Restore** reads it back. Clearing browser data erases the lot, and no copy
exists anywhere else. Worth doing every few weeks and before changing phones.

The same screen has **Erase all data**, which deletes everything on this device
and cannot be undone. **Reset programme to defaults** sits next to it and is
much milder: it restores the stock workouts and exercises and keeps all of your
history.

## Offline

After the first successful load the service worker caches the app shell, so it
opens and works with no internet. Your data was never coming from the network
anyway.

## Reporting a problem

**Settings → About** shows the build number and a **Copy diagnostics** button.
That copies device, browser, storage state and how many things you have logged —
counts only, never what you entered. Paste it into your bug report; the build
number is most of the diagnosis.

## Updating

Replace the files below and commit. Then close the app fully and reopen it
**twice** — a service worker hands over on the second launch. Confirm the new
build under **Settings → About**.

## Deploying your own copy

    Settings → Pages → Build and deployment
      Source: Deploy from a branch
      Branch: main      Folder: / (root)
      Save

Wait 1–3 minutes, then open `https://<user>.github.io/<repo>/` (keep the
trailing slash). Every path in the app is relative, so it also works at a
domain root or any subpath.

> On a free GitHub account, Pages requires a **public** repository. GitHub Pro
> allows Pages from a private repo, but the published site is public either way.
> That is fine here: the code contains no personal data.

## Files

    index.html              the entire application
    manifest.webmanifest    PWA metadata (name, icons, standalone display)
    sw.js                   service worker — offline caching
    .nojekyll               tells GitHub Pages to skip Jekyll
    icons/                  home screen and install icons

---

Not a medical device. It does not diagnose anything. Persistent pain, symptoms
or unusual physiological readings belong with a qualified healthcare
professional, separately from any training decision.
