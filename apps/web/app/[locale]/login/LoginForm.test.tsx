import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const signIn = vi.fn();
const useAuth = vi.fn(() => ({ signIn }));
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

import { LoginForm } from "./LoginForm";

const LABELS = {
  email: "Email",
  password: "Password",
  submit: "Sign in",
  registerPrompt: "Don't have an account?",
  registerLink: "Create one",
};

describe("LoginForm (Tracking + Notifications)", () => {
  beforeEach(() => {
    signIn.mockReset();
    push.mockReset();
  });

  it("signs in and redirects to the dashboard on success", async () => {
    signIn.mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    render(<LoginForm labels={LABELS} />);

    await user.type(screen.getByLabelText("Email"), "a@example-test.invalid");
    await user.type(screen.getByLabelText("Password"), "a-strong-password-1");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => {
      expect(signIn).toHaveBeenCalledWith("a@example-test.invalid", "a-strong-password-1");
    });
    expect(push).toHaveBeenCalledWith("/dashboard/tracking");
  });

  it("shows an accessible error and does not redirect on failure", async () => {
    signIn.mockResolvedValue({ ok: false, error: "Incorrect email or password." });
    const user = userEvent.setup();
    render(<LoginForm labels={LABELS} />);

    await user.type(screen.getByLabelText("Email"), "a@example-test.invalid");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password.");
    expect(push).not.toHaveBeenCalled();
  });
});
