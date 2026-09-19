# Store readiness checklist — Apple App Store & Google Play

**Status: not ready to publish. This is a to-do list, not a compliance
claim.**

Nothing in this file asserts that Baseline complies with Apple's or Google's
policies. Those determinations are made by the reviewers at those companies
and, where legal questions are involved, by a lawyer. This lists what is done,
what is not, and what needs someone other than an engineer.

Baseline today is a web app. Publishing to either store means wrapping it
(Capacitor, a Trusted Web Activity, or similar) or rebuilding it natively —
which changes several answers below, especially about storage and permissions.

---

## Already true of the implementation

- [x] Processing happens entirely on the device
- [x] No account, no server, no remote database
- [x] No analytics, telemetry, crash reporting or advertising SDKs
- [x] No third-party libraries at all
- [x] Health data is never transmitted
- [x] In-app explanation of what imported data is used for, before import
- [x] Expandable "How your data is used" detail
- [x] User-accessible deletion of imported data, reporting what was deleted
- [x] User-accessible erase-of-everything
- [x] Data export, so nothing is held hostage
- [x] Upload validation: type, size, content, row count
- [x] Privacy-preserving defaults (no sharing, no analytics, alerts off)
- [x] A written privacy policy describing the actual implementation
  (`PRIVACY.md`)
- [x] "Not a medical device" disclaimer in the app

---

## Required before submission — engineering

- [ ] **Host the privacy policy at a public URL.** Both stores require a
      URL, not a file in a repository.
- [ ] **Decide the wrapper** (Capacitor / TWA / native) and re-audit storage:
      a WebView's IndexedDB lives in the app sandbox and is included in
      device backups (iCloud, Google) unless excluded. That changes what
      §"Where it is stored" in `PRIVACY.md` must say.
- [ ] **Re-check the backup story.** If the OS backs up the app container,
      health data leaves the device inside that backup. Either exclude it or
      say so plainly.
- [ ] **Add a Content Security Policy** (`<meta http-equiv>` at minimum). Not
      possible to set as a header on GitHub Pages; possible inside a wrapper.
- [ ] **Version and build identifiers** for store metadata.
- [ ] **Age rating questionnaires** — both stores ask about health content.
- [ ] Confirm no export of the app binary contains any developer test data.

## Required before submission — disclosures

- [ ] **Apple App Privacy ("nutrition label")** — declare Health & Fitness
      data as collected-or-not. As implemented, data is neither collected by
      the developer nor linked to an identity nor used for tracking, because
      it never leaves the device. This must be re-checked after wrapping.
- [ ] **Apple: no tracking**, so no App Tracking Transparency prompt is
      needed. Re-check if anything is ever added.
- [ ] **Google Play Data Safety form** — declare Health and fitness data;
      state whether it is collected, shared, encrypted in transit (n/a if
      never transmitted) and whether deletion is offered (it is).
- [ ] **Google Play Health apps declaration**, if the listing uses a health
      category.
- [ ] **Account deletion requirement (Google Play)** — Baseline has no
      account. Confirm how the policy applies to an accountless app and
      document the answer.
- [ ] Data-deletion instructions in the store listing itself.

## Required before submission — legal and trademark

**None of this can be settled inside this repository.**

- [ ] **WHOOP trademark use.** The app names WHOOP to identify the source of
      a file the user chose. Review against WHOOP's trademark and brand
      guidelines, and against each store's rules on third-party marks in
      names, icons, screenshots and descriptions. Do not use WHOOP's logo.
- [ ] **WHOOP's terms covering exported data.** Whether a third-party app may
      process a user's own export, and under what conditions. Not answered
      here, and must not be assumed either way.
- [ ] **Same review for every other service named** (Garmin, Oura, Fitbit,
      Polar, Samsung, Apple Health).
- [ ] **Which data-protection regimes apply** (GDPR / UK GDPR / CCPA /
      others), and in what role. Depends on who publishes it and where.
- [ ] **Whether the "not a medical device" disclaimer is sufficient** in each
      market of intended distribution.
- [ ] **Publisher identity, contact address and support URL** — placeholders
      in `PRIVACY.md` must be filled with real, accurate details.
- [ ] Legal review of `PRIVACY.md` as written.

## Explicitly out of scope unless asked for

- Apple HealthKit — **not implemented**. Adding it brings entitlements, a
  usage-description string, and Apple's specific HealthKit privacy rules,
  including the prohibition on using HealthKit data for advertising.
- Google Health Connect — **not implemented**. Adding it brings its own
  permissions and declaration form.
- Any WHOOP API integration — **not implemented**, and out of scope. Baseline
  reads a file the user exported.
- Accounts, sync, cloud backup, sharing — none implemented.

---

## Re-audit before each submission

```
python audit_privacy.py    # data flow, network, storage, logging, leakage
python verify_web.py       # gates the shipped build
cycle.ps1                  # test suite, including the privacy tests
```

If any of those stop passing, the answers above are no longer true.
