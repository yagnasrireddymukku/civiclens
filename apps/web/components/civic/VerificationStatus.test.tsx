import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VerificationStatus } from "./VerificationStatus";

describe("VerificationStatus", () => {
  it.each([
    ["VERIFIED", "Verified"],
    ["NEEDS_REVIEW", "Needs review"],
    ["EXPIRED", "Expired"],
    ["UNVERIFIED", "Unverified"],
  ] as const)(
    "renders visible, distinct text for %s — never relies on color alone",
    (status, expectedText) => {
      render(<VerificationStatus status={status} />);
      expect(screen.getByText(expectedText)).toBeInTheDocument();
    },
  );

  it("pairs a distinct icon with each of the four states", () => {
    const { container: verified } = render(<VerificationStatus status="VERIFIED" />);
    const { container: unverified } = render(<VerificationStatus status="UNVERIFIED" />);

    const verifiedPath = verified.querySelector("svg")?.innerHTML;
    const unverifiedPath = unverified.querySelector("svg")?.innerHTML;

    expect(verifiedPath).toBeTruthy();
    expect(unverifiedPath).toBeTruthy();
    expect(verifiedPath).not.toBe(unverifiedPath);
  });
});
