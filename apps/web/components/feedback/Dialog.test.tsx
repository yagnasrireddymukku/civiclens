import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Dialog } from "./Dialog";

describe("Dialog", () => {
  it("is not open when `open` is false, and opens when it becomes true", () => {
    const { rerender } = render(
      <Dialog open={false} onClose={() => {}} title="Example dialog">
        <p>Body content</p>
      </Dialog>,
    );

    expect(screen.getByText("Example dialog")).not.toBeVisible();

    rerender(
      <Dialog open onClose={() => {}} title="Example dialog">
        <p>Body content</p>
      </Dialog>,
    );

    expect(screen.getByText("Example dialog")).toBeVisible();
  });

  it("calls onClose when the close button is activated", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(
      <Dialog open onClose={onClose} title="Example dialog">
        <p>Body content</p>
      </Dialog>,
    );

    await user.click(screen.getByRole("button", { name: "Close dialog" }));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("labels the dialog with its title for assistive tech", () => {
    render(
      <Dialog open onClose={() => {}} title="Example dialog">
        <p>Body content</p>
      </Dialog>,
    );

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAccessibleName("Example dialog");
  });
});
