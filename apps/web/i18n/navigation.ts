import { createNavigation } from "next-intl/navigation";
import { routing } from "./routing";

/**
 * Locale-aware Link/useRouter/usePathname/redirect — always prefer these
 * over next/link and next/navigation in components, so a link authored
 * for one locale automatically stays within it.
 */
export const { Link, redirect, usePathname, useRouter, getPathname } = createNavigation(routing);
