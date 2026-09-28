import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const askCivicAI = vi.fn();
vi.mock("@/lib/ai", () => ({
  askCivicAI: (...args: unknown[]) => askCivicAI(...args),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

import { AskCivicAIForm } from "./AskCivicAIForm";

const LABELS = {
  questionLabel: "Your question",
  questionHint: "Ask about a published job, service, scheme, or document (3 to 500 characters).",
  submit: "Ask",
  loading: "Thinking…",
  resultHeading: "Answer",
  citationsHeading: "Sources",
  needsReviewCaveat: "This source is currently under re-review.",
  statusInsufficientEvidence: "CivicLens does not have enough published information.",
  statusProviderUnavailable: "Civic AI is not currently available.",
  statusUngrounded: "CivicLens could not find a reliably sourced answer.",
  searchLinkLabel: "Try CivicLens search instead",
  errorGeneric: "Could not get an answer",
  lastVerifiedLabel: "Last verified",
};

function baseResponse(overrides: Record<string, unknown> = {}) {
  return {
    grounding_status: "GROUNDED",
    answer: "This is a fictional fixture job.",
    citations: [
      {
        citation_id: 1,
        title: "Test Civic Clerk Recruitment (Fixture)",
        route: "/jobs/test-civic-clerk",
        source: {
          organization: "Test Board — Not Real",
          title: "Test Notice",
          url: "https://example-test.invalid",
        },
        verification_status: "VERIFIED",
        last_verified: "2026-08-01T00:00:00Z",
        needs_review_caveat: false,
      },
    ],
    message: "",
    disclaimer: "This is informational only, not an official government decision.",
    locale: "en",
    ...overrides,
  };
}

describe("AskCivicAIForm (Phase 12)", () => {
  beforeEach(() => {
    askCivicAI.mockReset();
  });

  it("rejects a too-short question before calling the API", async () => {
    const user = userEvent.setup();
    render(<AskCivicAIForm locale="en" labels={LABELS} />);

    await user.type(screen.getByLabelText("Your question"), "hi");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(askCivicAI).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("shows a grounded answer with its citation, source, and disclaimer", async () => {
    askCivicAI.mockResolvedValue({ reachable: true, data: baseResponse() });
    const user = userEvent.setup();
    render(<AskCivicAIForm locale="en" labels={LABELS} />);

    await user.type(screen.getByLabelText("Your question"), "What is this job about?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() =>
      expect(screen.getByText("This is a fictional fixture job.")).toBeInTheDocument(),
    );
    const link = screen.getByRole("link", { name: "Test Civic Clerk Recruitment (Fixture)" });
    expect(link).toHaveAttribute("href", "/jobs/test-civic-clerk");
    expect(screen.getByText(/informational only/)).toBeInTheDocument();
  });

  it("shows a visible caveat for a needs-review source", async () => {
    askCivicAI.mockResolvedValue({
      reachable: true,
      data: baseResponse({
        citations: [
          {
            citation_id: 1,
            title: "Test Job (Fixture)",
            route: "/jobs/test-job",
            source: {
              organization: "Test Board",
              title: "Test Notice",
              url: "https://example-test.invalid",
            },
            verification_status: "NEEDS_REVIEW",
            last_verified: null,
            needs_review_caveat: true,
          },
        ],
      }),
    });
    const user = userEvent.setup();
    render(<AskCivicAIForm locale="en" labels={LABELS} />);

    await user.type(screen.getByLabelText("Your question"), "What is this job about?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() =>
      expect(screen.getByText("This source is currently under re-review.")).toBeInTheDocument(),
    );
  });

  it("shows the insufficient-evidence state distinctly, with a link to search", async () => {
    askCivicAI.mockResolvedValue({
      reachable: true,
      data: baseResponse({
        grounding_status: "INSUFFICIENT_EVIDENCE",
        answer: null,
        citations: [],
      }),
    });
    const user = userEvent.setup();
    render(<AskCivicAIForm locale="en" labels={LABELS} />);

    await user.type(screen.getByLabelText("Your question"), "Something totally unrelated?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() =>
      expect(
        screen.getByText("CivicLens does not have enough published information."),
      ).toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: "Try CivicLens search instead" })).toHaveAttribute(
      "href",
      "/search",
    );
  });

  it("shows the provider-unavailable state distinctly from insufficient evidence", async () => {
    askCivicAI.mockResolvedValue({
      reachable: true,
      data: baseResponse({ grounding_status: "PROVIDER_UNAVAILABLE", answer: null, citations: [] }),
    });
    const user = userEvent.setup();
    render(<AskCivicAIForm locale="en" labels={LABELS} />);

    await user.type(screen.getByLabelText("Your question"), "What is this job about?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() =>
      expect(screen.getByText("Civic AI is not currently available.")).toBeInTheDocument(),
    );
  });

  it("shows the ungrounded state and never renders a null answer as text", async () => {
    askCivicAI.mockResolvedValue({
      reachable: true,
      data: baseResponse({ grounding_status: "UNGROUNDED", answer: null, citations: [] }),
    });
    const user = userEvent.setup();
    render(<AskCivicAIForm locale="en" labels={LABELS} />);

    await user.type(screen.getByLabelText("Your question"), "What is this job about?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() =>
      expect(
        screen.getByText("CivicLens could not find a reliably sourced answer."),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByText("null")).not.toBeInTheDocument();
  });

  it("shows an honest error state, not a crash, when the API is unreachable", async () => {
    askCivicAI.mockResolvedValue({ reachable: false, error: "Network error" });
    const user = userEvent.setup();
    render(<AskCivicAIForm locale="en" labels={LABELS} />);

    await user.type(screen.getByLabelText("Your question"), "What is this job about?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByText(/Could not get an answer/)).toBeInTheDocument();
  });

  it("renders the result region as an accessible live status update", async () => {
    askCivicAI.mockResolvedValue({ reachable: true, data: baseResponse() });
    const user = userEvent.setup();
    render(<AskCivicAIForm locale="en" labels={LABELS} />);

    await user.type(screen.getByLabelText("Your question"), "What is this job about?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(screen.getByRole("status")).toBeInTheDocument());
  });
});
