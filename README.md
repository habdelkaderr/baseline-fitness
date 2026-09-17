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
   what you lifted last time, plus and minus buttons for reps and weight, and
   a rest timer that starts itself when you finish a set.
6. Played football instead? **Log activity** takes three taps. It feeds
   straight into tomorrow's recommendation.

## Finding your way around

Four sections along the bottom:

| | |
|---|---|
| **Today** | Readiness, today's session, log an activity |
| **Train** | Your programme, exercise library, warm-ups, history |
| **Activity** | Everything you have done, planned or not |
| **Progress** | Weekly review, strength, tests, measurements, patterns |

**Settings** is the gear in the top right. Wearable numbers and trends live
behind the readiness row on Today, so if you do not use a tracker you never see
an empty chart.

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

**Settings → App** shows the build number and a **Copy diagnostics** button.
That copies device, browser, storage state and how many things you have logged —
counts only, never what you entered. Paste it into your bug report; the build
number is most of the diagnosis.

## Updating

Replace the files below and commit. Then close the app fully and reopen it
**twice** — a service worker hands over on the second launch. Confirm the new
build under **Settings → App**.

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
