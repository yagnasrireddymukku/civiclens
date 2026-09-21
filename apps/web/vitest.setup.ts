import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import "@testing-library/jest-dom/vitest";

// vitest.config.ts sets `test.globals: false` (explicit imports
// throughout the suite), which means @testing-library/react's automatic
// afterEach(cleanup) never registers (it only self-registers when it
// detects globally-injected test hooks). Without this, renders from one
// test leak into the next test in the same file — register it centrally
// here instead of remembering it per test file.
afterEach(() => {
  cleanup();
});

// jsdom (as of v25) does not implement HTMLDialogElement.showModal()/close()
// — see https://github.com/jsdom/jsdom/issues/3294. Components built on
// the native <dialog> element (components/feedback/Dialog.tsx) need this
// minimal polyfill to be testable at all; it mirrors only the
// open-state/event behavior our components rely on, not full top-layer
// or focus-trap semantics (which jsdom cannot provide either way).
if (typeof HTMLDialogElement !== "undefined" && !HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
    const wasOpen = this.hasAttribute("open");
    this.removeAttribute("open");
    if (wasOpen) {
      this.dispatchEvent(new Event("close"));
    }
  };
}
