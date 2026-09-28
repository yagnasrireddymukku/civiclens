import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const signUp = vi.fn();
const useAuth = vi.fn(() => ({ signUp }));
vi.mock("@/components/auth", () => ({
  useAuth: () => useAuth(),
}));

const push = vi.fn();
vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ push }),
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

import { RegisterForm } from "./RegisterForm";

const LABELS = {
  email: "Email",
  password: "Password",
  passwordHint: "At least 10 characters.",
  submit: "Create account",
  loginPrompt: "Already have an account?",
  loginLink: "Sign in",
};

describe("RegisterForm (Tracking + Notifications)", () => {
  beforeEach(() => {
    signUp.mockReset();
    push.mockReset();
  });

  it("creates an account and redirects to the dashboard on success", async () => {
    signUp.mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    render(<RegisterForm labels={LABELS} />);

    await user.type(screen.getByLabelText("Email"), "a@example-test.invalid");
    await user.type(screen.getByLabelText("Password"), "a-strong-password-1");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() => {
      expect(signUp).toHaveBeenCalledWith("a@example-test.invalid", "a-strong-password-1");
    });
    expect(push).toHaveBeenCalledWith("/dashboard/tracking");
  });

  it("shows an accessible error and does not redirect when the email is already registered", async () => {
    signUp.mockResolvedValue({ ok: false, error: "An account with this email already exists." });
    const user = userEvent.setup();
    render(<RegisterForm labels={LABELS} />);

    await user.type(screen.getByLabelText("Email"), "a@example-test.invalid");
    await user.type(screen.getByLabelText("Password"), "a-strong-password-1");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "An account with this email already exists.",
    );
    expect(push).not.toHaveBeenCalled();
  });
});
