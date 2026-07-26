// Shared text-search helpers for client-side filtering of small, fully-loaded
// lists (schedule, voting participants). Kept dependency-free on purpose: the
// datasets are tiny and live in the client, so normalize + token matching
// covers the real pain (case, ё/е, punctuation, word order) without the bundle
// cost or ranking side effects of a fuzzy library.

// Strip combining diacritical marks (e.g. accented Latin letters in titles)
// after NFD decomposition so "é" matches "e".
const COMBINING_MARKS = /[̀-ͯ]/g;

// Collapse anything that isn't a letter or digit into a single space so
// punctuation never blocks a match ("re:zero" matches "re zero").
const NON_ALPHANUMERIC = /[^\p{L}\p{N}]+/gu;

/**
 * Normalize text for searching: lowercase, fold ё→е, drop diacritics, and
 * reduce punctuation/whitespace runs to single spaces. Returns a trimmed
 * string safe to substring-match against.
 */
export function normalizeSearchText(value: string): string {
	return value
		.normalize('NFD')
		.replace(COMBINING_MARKS, '')
		.toLowerCase()
		.replace(/ё/g, 'е')
		.replace(NON_ALPHANUMERIC, ' ')
		.trim();
}

/**
 * Split a raw query into normalized search tokens. Empty query → no tokens,
 * which callers treat as "match everything".
 */
export function tokenizeQuery(query: string): string[] {
	const normalized = normalizeSearchText(query);
	return normalized.length === 0 ? [] : normalized.split(' ');
}

/**
 * Fold a row's searchable fields into one normalized haystack. Fields are
 * joined by a space, which cannot merge two of them into a false match: tokens
 * never contain spaces, so no token can span the join. Null/undefined fields
 * are ignored.
 *
 * Build this once per row when the data changes, not once per keystroke —
 * `normalizeSearchText` runs an NFD decomposition plus three regex passes, and
 * a filter that re-normalizes the whole list on every input event is what turns
 * typing in a several-hundred-row schedule into a janky interaction.
 */
export function buildSearchHaystack(fields: Array<string | number | null | undefined>): string {
	return fields
		.filter((field) => field !== null && field !== undefined)
		.map((field) => normalizeSearchText(String(field)))
		.join(' ');
}

/**
 * True when every token appears as a substring of the haystack. AND-matching
 * across tokens lets users type words in any order ("наруто опенинг" matches
 * "Опенинг: Наруто"). No tokens (empty query) matches everything.
 */
export function matchesTokens(tokens: string[], haystack: string): boolean {
	return tokens.every((token) => haystack.includes(token));
}
