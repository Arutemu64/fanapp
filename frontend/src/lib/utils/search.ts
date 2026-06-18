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
 * True when every query token appears as a substring somewhere in the given
 * fields. AND-matching across tokens lets users type words in any order
 * ("наруто опенинг" matches "Опенинг: Наруто"); each field is matched
 * independently so a token may hit the title and another the nomination.
 * Null/undefined fields are ignored.
 */
export function matchesSearch(
	query: string,
	fields: Array<string | number | null | undefined>
): boolean {
	const tokens = tokenizeQuery(query);
	if (tokens.length === 0) return true;

	const haystacks = fields
		.filter((field) => field !== null && field !== undefined)
		.map((field) => normalizeSearchText(String(field)));

	return tokens.every((token) => haystacks.some((haystack) => haystack.includes(token)));
}
