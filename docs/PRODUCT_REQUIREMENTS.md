# CivicLens — Product Requirements

Companion to [PRODUCT.md](PRODUCT.md). This document defines functional and
non-functional requirements at a level concrete enough to drive architecture
and phase planning ([ROADMAP.md](ROADMAP.md)), without prescribing UI or
implementation.

## 1. Functional Requirements by Domain

### 1.1 Government Jobs & Exams
- FR-J1: Users can browse and search job notifications by organization,
  department, qualification, location, and status (upcoming/open/closed).
- FR-J2: Each job notification links to its exam(s) and timeline stages
  (notification, application window, correction window, admit card, exam
  date, answer key, result, subsequent stages).
- FR-J3: Each notification exposes source, published date, retrieved date,
  last-verified date, and verification status.
- FR-J4: Users can view eligibility criteria as structured data (age,
  qualification, category, domicile, etc.), not only as prose.

### 1.2 Government Services, Schemes, Scholarships
- FR-S1: Users can browse services/schemes/scholarships by category, state,
  district, and target beneficiary group.
- FR-S2: Each entry shows purpose, eligibility, required documents, process
  steps, issuing department, and official source.
- FR-S3: Scholarships expose award amount, application window, and renewal
  conditions where applicable, all sourced.

### 1.3 Representatives & Elections
- FR-R1: Users can look up representatives (MLA/MP/Minister/CM) by
  constituency or state, with term dates and source.
- FR-R2: Election records show factual results (candidate, party, votes,
  outcome, date) with source and verification status.
- FR-R3: No ranking, scoring, or recommendation is ever attached to a
  representative or party. See [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md) §5.

### 1.4 Documents & Certificates
- FR-D1: Users can look up a document/certificate type and see purpose,
  issuing authority, required inputs, and official application channel.

### 1.5 Eligibility & Calculators
- FR-E1: Users can check structured eligibility for a given opportunity
  against explicit attributes they provide (age, qualification, income,
  category, domicile, etc.).
- FR-E2: Every eligibility result shows which rules passed/failed and why,
  in plain language, with a link to the authoritative source rule.
- FR-E3: Calculators (e.g., age-as-on-date, income-eligibility) are
  deterministic and independently testable.

### 1.6 Civic Search
- FR-SR1: Keyword and natural-language search across all published entities.
- FR-SR2: Filters by domain, state, district, status, and date.
- FR-SR3: Typo-tolerant and autocomplete search (see [SEARCH.md](SEARCH.md)).
- FR-SR4: English and Telugu query support at launch.

### 1.7 Civic AI
- FR-AI1: Users can ask natural-language questions and receive answers
  grounded in retrieved structured data and approved documents, with
  inline source citations.
- FR-AI2: The system must indicate when it cannot answer confidently rather
  than fabricate an answer. See [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md).
- FR-AI3: The AI layer must never issue an eligibility verdict that bypasses
  the Eligibility Engine.

### 1.8 Tracking & Alerts
- FR-T1: Authenticated users can track jobs, exams, schemes, services, or
  specific deadlines.
- FR-T2: Users are notified when a tracked item's structured data changes in
  a materially relevant way (date change, status change, new stage).

### 1.9 Personal Civic Dashboard
- FR-P1: Authenticated users can view saved items, tracked items, upcoming
  deadlines, and (where explicitly provided) a document checklist.
- FR-P2: Personalization is based only on data the user explicitly provides
  or actions they explicitly take — never inferred sensitive attributes.

## 2. Non-Functional Requirements

### 2.1 Trust & Accuracy
- NFR-T1: No factual claim about a scheme, job, date, salary, URL,
  representative, or election result may be invented. See
  [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md).
- NFR-T2: Every time-sensitive page displays "Last verified: DATE" and a
  source link.
- NFR-T3: Unverifiable information is marked `UNVERIFIED` or `NEEDS_REVIEW`,
  never presented as fact.

### 2.2 Performance
- NFR-P1: Search results return in a perceptibly fast time on median mobile
  network conditions in India (target: sub-second server response for
  indexed queries at MVP scale).
- NFR-P2: Public content pages are optimized for fast first paint (Core Web
  Vitals) given SEO importance (see [SEO.md](SEO.md)).

### 2.3 Availability & Data Integrity
- NFR-A1: Structured data changes are auditable — every material change to
  a published fact must be traceable to a change record and a source
  version. See [DATABASE.md](DATABASE.md) §change_records.
- NFR-A2: The system distinguishes soft-deleted/retired entities from
  active ones; nothing is silently destroyed.

### 2.4 Security & Privacy
- NFR-SEC1–SEC-n: see [SECURITY.md](SECURITY.md).
- NFR-PRIV1–PRIV-n: see [PRIVACY.md](PRIVACY.md). Data minimization is a
  hard requirement: no collection of sensitive personal data without a
  named product requirement it serves.

### 2.5 Accessibility
- NFR-ACC1: Public pages meet WCAG 2.2 AA at minimum (raised from 2.1 AA
  during Phase 4 — 2.2 is a superset of 2.1's criteria, so this is a
  higher bar, not a different one).
- NFR-ACC2: Core flows (search, view opportunity, check eligibility) are
  usable via keyboard and screen reader.

### 2.6 Internationalization
- NFR-I18N1: English and Telugu are first-class at launch, not
  machine-translated afterthoughts, for at least core navigation and
  domain content. See [ARCHITECTURE.md](ARCHITECTURE.md) §10.

### 2.7 Scalability
- NFR-SC1: The architecture must support extension to additional Indian
  states without core schema or API redesign (state/district are data, not
  code). See [ARCHITECTURE.md](ARCHITECTURE.md) §3.

## 3. Explicit Out-of-Scope for v1

- Full India coverage (AP + Telangana only)
- Push notifications via SMS/WhatsApp (email/in-app only at v1; see
  [ROADMAP.md](ROADMAP.md) Phase 12)
- Payments/premium tiers (architected for, not built — see
  [MONETIZATION.md](MONETIZATION.md))
- Automated ingestion running unattended in production (human-in-the-loop
  review is mandatory at v1 — see [DATA_SOURCES.md](DATA_SOURCES.md) §4)

## 4. Acceptance Lens

A feature is not "done" until:
1. It has a documented, testable specification (this class of document)
2. Structured data behind it has explicit source/verification fields
3. It has deterministic tests where determinism is expected (eligibility,
   calculators)
4. It degrades honestly (shows "unverified"/"no result") rather than
   guessing
