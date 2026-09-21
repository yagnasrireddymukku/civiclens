"use client";

import { useState } from "react";
import { useRouter } from "@/i18n/navigation";
import { Pagination } from "@/components/navigation";
import { SearchBar, type SearchBarState } from "@/components/civic";

export interface SearchControlsProps {
  initialQuery: string;
  label: string;
  placeholder: string;
  state: SearchBarState;
  errorMessage?: string;
  page: number;
  totalPages: number;
}

/**
 * The only interactive part of the search page — everything else is
 * server-rendered from `searchParams` (page.tsx). Both the query submit
 * and page-change navigate to a new `?q=&page=` URL rather than holding
 * client-side result state, so results stay shareable/bookmarkable
 * (this phase's requirement) and a page reload always reproduces them.
 */
export function SearchControls({
  initialQuery,
  label,
  placeholder,
  state,
  errorMessage,
  page,
  totalPages,
}: SearchControlsProps) {
  const [value, setValue] = useState(initialQuery);
  const router = useRouter();

  function handleSubmit(query: string) {
    const trimmed = query.trim();
    router.push(trimmed ? { pathname: "/search", query: { q: trimmed } } : { pathname: "/search" });
  }

  function handlePageChange(nextPage: number) {
    router.push({
      pathname: "/search",
      query: initialQuery ? { q: initialQuery, page: String(nextPage) } : {},
    });
  }

  return (
    <>
      <SearchBar
        value={value}
        onChange={setValue}
        onSubmit={handleSubmit}
        state={state}
        placeholder={placeholder}
        errorMessage={errorMessage}
        label={label}
      />
      <Pagination page={page} totalPages={totalPages} onPageChange={handlePageChange} />
    </>
  );
}
