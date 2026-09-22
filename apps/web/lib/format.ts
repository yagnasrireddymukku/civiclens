/**
 * Humanizes a backend `SCREAMING_SNAKE_CASE` enum/free-text value for
 * display (e.g. "PERMANENT" -> "Permanent", "AUTONOMOUS_BODY" ->
 * "Autonomous Body") — never a hardcoded per-value lookup, since new
 * domain-defined values (entity types, categories, org types) can be
 * added on the backend without a frontend change.
 */
export function humanizeEnumValue(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .filter(Boolean)
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}
