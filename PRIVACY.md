# Baseline — Privacy Policy

**Last updated:** _[DATE — fill in on publication]_
**Published by:** _[PUBLISHER NAME — placeholder, not yet decided]_
**Contact:** _[CONTACT EMAIL OR ADDRESS — placeholder, not yet decided]_

> The placeholders above are deliberate. This policy describes the software
> accurately; it does not invent a company, an address, a jurisdiction or a
> certification that does not exist. They must be completed before this is
> published anywhere.

---

## The short version

Baseline runs entirely in your browser, on your device. The fitness data you
import is read by the page, used to work out your readiness and your training,
and stored in your browser's own database on that device.

**It is never uploaded. There is no account, no server and no analytics.** You
can delete it at any time, and doing so deletes it.

---

## 1. Who this applies to

Anyone who opens Baseline. You do not create an account, because there is no
account to create.

## 2. What data is involved

### Data you import

Baseline can read CSV files that you export from a wearable or fitness
service — WHOOP, Garmin, Oura, Fitbit, Polar, Samsung, Apple Health and
others. From those files it reads and keeps:

- the date of each day
- recovery or readiness score
- heart-rate variability
- resting heart rate
- sleep duration and sleep performance
- day strain or training load
- individual workouts: start time, activity name, duration, strain
- journal questions and their yes/no answers

**It does not keep the free-text notes** in a WHOOP journal export. Those are
read past and discarded.

**It does not keep the file.** The file is read into memory, the figures above
are taken out of it, and the text is released.

### Data you enter

Daily check-ins (sleep, energy, soreness, stress, motivation, pain), training
sessions and the sets in them, activities, fitness tests, body measurements,
your profile (name, age, height, weight, sex, equipment, goals, sports), and —
only if you switch it on — menstrual-cycle entries.

### Data that is generated

Your readiness score, personal baselines, the daily training recommendation,
weekly totals and progress figures. All calculated on your device from the two
categories above.

### Data that is not collected

No account identifiers. No email address. No advertising identifier. No
location. No contacts. No device fingerprint. No usage analytics. No crash
reports. No behavioural profile.

## 3. Why it is processed

To do the one thing Baseline does: work out how ready you are to train today,
and recommend a session that matches. Recovery, HRV, resting heart rate and
sleep produce the readiness score; your training history decides which session
is due; your profile decides which exercises are possible with the equipment
you have.

There is no secondary purpose. The data is not used for advertising, is not
sold, is not shared, and is not used to train any model.

## 4. Where processing happens

**On your device, in your browser.** Baseline is a single web page with no
backend. There is no server that could receive your data, because there is no
server.

## 5. Where it is stored

In your browser's own storage, on the device you used:

- **IndexedDB** (a database named `baseline`) holds everything.
- **Local storage** holds your theme preference and, while one is running, an
  in-progress workout so it survives a closed tab.
- On a browser where IndexedDB is unavailable, Baseline falls back to storing
  the whole dataset in local storage instead, so that your history is not
  silently lost. In that case your imported data is in local storage on that
  device. Both deletion options below clear it either way.

Storage is per-browser and per-device. Baseline on your phone and Baseline on
your laptop know nothing about each other. Moving data between them is a file
you export and import yourself.

## 6. What is sent off your device

**Nothing.**

Baseline makes no network requests once the page has loaded. It contains no
analytics, no telemetry, no crash reporting, no advertising code, no fonts or
scripts loaded from elsewhere, and no third-party libraries at all.

The one unavoidable exception is the ordinary act of loading the page: the
web host that serves Baseline can see the request for the page itself —
your IP address, your browser's user agent and the time — exactly as any
website can. It receives no fitness or health data, because none is sent. If
you install Baseline to your home screen and use it offline, even that request
stops.

## 7. Third parties

No third-party service receives your data. Specifically: no AI or language
model service, no analytics provider, no crash-reporting service, no logging
service, no authentication provider, no remote database, no cloud storage and
no advertising network.

The **web host** serving the page is described in section 6.

If a version of Baseline ever sends anything anywhere, this section must say
what, to whom, and why — before that version ships.

## 8. How long it is kept

Until you delete it. There is no automatic expiry: a training history that
erased itself would not be a training history.

The contents of an imported file exist only in memory, during the import.

## 9. How you delete it

In **Settings → Data**:

- **"Delete imported data"** removes everything that came from an import —
  imported days, workouts, journal rows, the import history, and the baselines
  calculated from them. It tells you exactly what was removed. Your own
  sessions, activities, check-ins and settings are kept.
- **"Erase all data"** removes everything Baseline holds on that device and
  returns it to a first run.

You can also clear the site's data in your browser settings, which removes
everything, because everything is in the browser. Deleting the app from your
home screen removes it too.

Because nothing was ever uploaded, there is nothing to request the deletion of
from anyone else, and no one to ask.

## 10. Security

- Data stays on your device, which removes the entire category of risk that
  comes from transmitting and storing it elsewhere.
- Imported files are checked before they are read: type, size (25 MB limit),
  and whether they are text at all. Unrecognised files are rejected with a
  reason rather than imported as the wrong thing.
- Imported content is never executed. It is treated as text and escaped before
  it is displayed.
- Your health data is never written to the browser console or into a URL.
- The page loads no code from anywhere else, so there is no supply chain to
  compromise.

**What this does not protect against:** Baseline has no password or passcode
of its own. Anyone who can unlock your device and open the app can see your
data. Use your device's own lock screen. A backup file you export is plain,
unencrypted JSON — it is readable by anything that can read a file, so keep it
somewhere you are comfortable with.

## 11. Your choices

- Baseline works with no imported data at all — daily check-ins alone are
  enough. Importing is optional.
- Cycle tracking is off until you turn it on, and can be deleted separately.
- Sound is on and alerts are off by default; alerts are local to your device
  and ask permission when you enable them.
- Everything can be exported as a file you control, and deleted.

Depending on where you live you may have statutory rights over your personal
data — to access it, correct it, export it or erase it. In Baseline these are
not requests you have to make of anyone: the data is on your device, the app
shows all of it, exports all of it, and deletes all of it on demand.

## 12. Children

Baseline is not designed for or directed at children.

## 13. About WHOOP and other services

Baseline is **not affiliated with, endorsed by, sponsored by or connected to**
WHOOP, Garmin, Oura, Fitbit, Polar, Samsung, Apple or any other company whose
export format it can read. Those names are used only to identify which service
a file you chose came from.

Baseline does **not** connect to any of those services. It has no integration,
uses no API, asks for no password and accesses no account. It reads a file
that you exported yourself and chose yourself.

Only import data you are authorised to provide.

## 14. Not a medical device

Baseline does not diagnose, treat, cure or prevent anything. It is a training
tool. Persistent symptoms, pain or unusual physiological readings belong with
a qualified healthcare professional, not an app.

## 15. Changes

If this policy changes, the date at the top changes. Because Baseline has no
account and no contact details for you, it cannot notify you; the current
version is always the one in the application and in this repository.

## 16. Contact

_[CONTACT — placeholder. Must be completed before publication.]_
