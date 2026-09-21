"use client";

import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  Divider,
  Input,
  RadioGroup,
  Select,
  Skeleton,
  Spinner,
  Switch,
  Textarea,
} from "@/components/primitives";
import { Alert, Dialog, Tooltip, useToast } from "@/components/feedback";
import { Breadcrumb, Dropdown, Pagination, Tabs } from "@/components/navigation";
import {
  DeadlineBadge,
  EligibilityStatus,
  InformationCard,
  LastVerified,
  OfficialSourceCard,
  SearchBar,
  SearchResultCard,
  SourceBadge,
  VerificationStatus,
} from "@/components/civic";
import styles from "./showcase.module.css";

const COLOR_TOKENS = [
  "primary",
  "primary-hover",
  "secondary",
  "accent",
  "success",
  "warning",
  "error",
  "info",
  "background",
  "surface",
  "border",
  "text-primary",
  "text-secondary",
  "text-muted",
];

const RADII = ["sm", "md", "lg", "xl", "pill"];
const SHADOWS = ["sm", "md", "lg"];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className={styles.section}>
      <h2 className={styles.sectionTitle}>{title}</h2>
      <div className={styles.sectionBody}>{children}</div>
    </section>
  );
}

function ToastDemoButtons() {
  const { showToast } = useToast();
  return (
    <div className={styles.row}>
      <Button size="sm" onClick={() => showToast("success", "Change approved.")}>
        Success toast
      </Button>
      <Button size="sm" onClick={() => showToast("error", "Could not save changes.")}>
        Error toast
      </Button>
    </div>
  );
}

export function DesignSystemShowcase({ locale }: { locale: string }) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [searchValue, setSearchValue] = useState("");
  const [page, setPage] = useState(1);
  const [inputValue, setInputValue] = useState("");

  return (
    <div className={styles.showcase}>
      <Section title="Color">
        <div className={styles.swatchGrid}>
          {COLOR_TOKENS.map((token) => (
            <div key={token} className={styles.swatch}>
              <div className={styles.swatchColor} style={{ background: `var(--color-${token})` }} />
              <code className={styles.swatchLabel}>--color-{token}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Typography">
        <p style={{ font: "var(--text-display)" }}>Display</p>
        <p style={{ font: "var(--text-h1)" }}>Heading 1</p>
        <p style={{ font: "var(--text-h2)" }}>Heading 2</p>
        <p style={{ font: "var(--text-h3)" }}>Heading 3</p>
        <p style={{ font: "var(--text-h4)" }}>Heading 4</p>
        <p style={{ font: "var(--text-body)" }}>Body text — the default reading size.</p>
        <p style={{ font: "var(--text-body-small)" }}>Body small — secondary information.</p>
        <p style={{ font: "var(--text-caption)" }}>Caption — metadata and timestamps.</p>
        <p style={{ font: "var(--text-label)" }}>LABEL</p>
      </Section>

      <Section title="Spacing">
        <div className={styles.row}>
          {[1, 2, 3, 4, 5, 6, 8, 10, 12].map((step) => (
            <div key={step} className={styles.spacingItem}>
              <div
                className={styles.spacingBox}
                style={{ width: `var(--space-${step})`, height: `var(--space-${step})` }}
              />
              <code>{step}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Radius">
        <div className={styles.row}>
          {RADII.map((radius) => (
            <div
              key={radius}
              className={styles.radiusBox}
              style={{ borderRadius: `var(--radius-${radius})` }}
            >
              {radius}
            </div>
          ))}
        </div>
      </Section>

      <Section title="Elevation">
        <div className={styles.row}>
          {SHADOWS.map((shadow) => (
            <div
              key={shadow}
              className={styles.shadowBox}
              style={{ boxShadow: `var(--shadow-${shadow})` }}
            >
              {shadow}
            </div>
          ))}
        </div>
      </Section>

      <Section title="Primitives — Buttons">
        <div className={styles.row}>
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Destructive</Button>
          <Button loading>Loading</Button>
          <Button disabled>Disabled</Button>
        </div>
        <div className={styles.row}>
          <Button size="sm">Small</Button>
          <Button size="md">Medium</Button>
          <Button size="lg">Large</Button>
        </div>
      </Section>

      <Section title="Primitives — Forms">
        <div className={styles.formGrid}>
          <Input
            label="Full name"
            placeholder="e.g. Test User — Not Real"
            hint="Shown as an example only."
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
          />
          <Input
            label="Email"
            type="email"
            error="Enter a valid email address."
            defaultValue="not-an-email"
          />
          <Textarea label="Notes" placeholder="Optional notes" />
          <Select
            label="State"
            placeholder="Select a state"
            options={[
              { value: "ZZ", label: "Testland (fixture)" },
              { value: "ZY", label: "Sampleland (fixture)" },
            ]}
          />
          <Checkbox label="I have read the disclaimer" />
          <RadioGroup
            legend="Preferred language"
            options={[
              { value: "en", label: "English" },
              { value: "te", label: "Telugu" },
            ]}
            defaultValue="en"
          />
          <Switch label="Email notifications" />
        </div>
      </Section>

      <Section title="Primitives — Surfaces">
        <div className={styles.row}>
          <Card>Default card</Card>
          <Card elevated>Elevated card</Card>
        </div>
        <div className={styles.row} style={{ marginTop: "var(--space-4)" }}>
          <Badge tone="neutral">Neutral</Badge>
          <Badge tone="primary">Primary</Badge>
          <Badge tone="success">Success</Badge>
          <Badge tone="warning">Warning</Badge>
          <Badge tone="error">Error</Badge>
          <Badge tone="info">Info</Badge>
        </div>
        <Divider />
        <div className={styles.row}>
          <Skeleton width="8rem" height="1rem" />
          <Skeleton width="2.5rem" height="2.5rem" circle />
          <Spinner label="Loading example" />
        </div>
      </Section>

      <Section title="Primitives — Overlays &amp; feedback">
        <div className={styles.row}>
          <Button onClick={() => setDialogOpen(true)}>Open dialog</Button>
          <Tooltip content="A CSS-only tooltip, no JS positioning library">
            <Button variant="secondary">Hover or focus me</Button>
          </Tooltip>
          <Dropdown
            label="Actions"
            items={[
              { label: "Track this item", onSelect: () => {} },
              { label: "Save for later", onSelect: () => {} },
            ]}
          />
          <ToastDemoButtons />
        </div>
        <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} title="Example dialog">
          <p>
            Built on the native &lt;dialog&gt; element — focus trapping and Escape-to-close come
            from the browser.
          </p>
        </Dialog>
        <div className={styles.stack}>
          <Alert tone="success" title="Change approved">
            An editor approved this update.
          </Alert>
          <Alert tone="warning" title="Needs review">
            A change was detected and is awaiting editorial review.
          </Alert>
          <Alert tone="error" title="Could not load">
            The request failed. Try again.
          </Alert>
          <Alert tone="info" title="Heads up">
            This is a neutral, informational message.
          </Alert>
        </div>
      </Section>

      <Section title="Navigation">
        <Breadcrumb
          items={[
            { label: "Home", href: "/" },
            { label: "Jobs (example)", href: "/dev/design-system" },
            { label: "Test Notice — Not Real" },
          ]}
        />
        <div style={{ marginTop: "var(--space-4)" }}>
          <Tabs
            label="Example tabs"
            items={[
              { value: "overview", label: "Overview", content: <p>Overview content.</p> },
              { value: "documents", label: "Documents", content: <p>Documents content.</p> },
              { value: "history", label: "History", content: <p>History content.</p> },
            ]}
          />
        </div>
        <div style={{ marginTop: "var(--space-4)" }}>
          <Pagination page={page} totalPages={5} onPageChange={setPage} />
        </div>
      </Section>

      <Section title="CivicLens components">
        <div className={styles.row}>
          <SourceBadge kind="official" />
          <SourceBadge kind="verified" />
          <SourceBadge kind="available" />
        </div>
        <div className={styles.row} style={{ marginTop: "var(--space-3)" }}>
          <VerificationStatus status="VERIFIED" />
          <VerificationStatus status="NEEDS_REVIEW" />
          <VerificationStatus status="EXPIRED" />
          <VerificationStatus status="UNVERIFIED" />
        </div>
        <div className={styles.row} style={{ marginTop: "var(--space-3)" }}>
          <EligibilityStatus status="ELIGIBLE" />
          <EligibilityStatus status="NOT_ELIGIBLE" />
          <EligibilityStatus status="INCOMPLETE" />
        </div>
        <div className={styles.row} style={{ marginTop: "var(--space-3)" }}>
          <DeadlineBadge status="UPCOMING" />
          <DeadlineBadge status="OPEN" />
          <DeadlineBadge status="CLOSING_SOON" />
          <DeadlineBadge status="CLOSED" />
        </div>
        <div style={{ marginTop: "var(--space-3)" }}>
          <LastVerified date={new Date("2026-08-01")} locale={locale} />
        </div>

        <Divider label="Cards" />
        <div className={styles.cardGrid}>
          <OfficialSourceCard
            organization="Test Board — Not Real"
            title="Sample Recruitment Notice (Fixture)"
            status="VERIFIED"
            lastVerifiedAt={new Date("2026-08-01")}
            locale={locale}
            url="https://example-test.invalid/notice/123"
          />
          <InformationCard
            eyebrow="Job (example)"
            title="Sample Recruitment Notice (Fixture)"
            description="A fictional example of a future job-listing card — no real notification exists yet."
            meta={["Testland", "Fixture only"]}
            badges={<SourceBadge kind="official" />}
            href="/dev/design-system"
          />
        </div>

        <Divider label="Search" />
        <SearchBar
          label="Search example"
          placeholder="Search jobs, schemes, services…"
          value={searchValue}
          onChange={setSearchValue}
          onSubmit={() => {}}
          state="idle"
        />
        <div style={{ marginTop: "var(--space-4)" }}>
          <SearchResultCard
            domain="Jobs (example)"
            title="Sample Recruitment Notice (Fixture)"
            snippet="A fictional search-result example demonstrating the reusable result card structure only."
            sourceKind="official"
            href="/dev/design-system"
          />
        </div>
      </Section>

      <Section title="Responsive behavior">
        <p>
          Resize the window, or use your browser&rsquo;s device toolbar, to see components adapt.
        </p>
      </Section>
    </div>
  );
}
