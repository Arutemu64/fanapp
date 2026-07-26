// Shared text-search helpers for client-side filtering of small, fully-loaded
// lists (schedule, voting participants). Kept dependency-free on purpose: the
// datasets are tiny and live in the client, so normalize + token matching
// covers the real pain (case, ё/е, punctuation, word order) without the bundle
// cost or ranking side effects of a fuzzy library.

// Strip combining diacritical marks (e.g. accented Latin letters in titles)
// after NFD decomposition so "é" matches "e". This is also what folds ё→е:
// NFD splits ё into е + U+0308, which this range then drops — so no separate
// ё replacement is needed (one was here once, and never fired). The ё/е tests
// in search.test.ts pin that behaviour.
const COMBINING_MARKS = /[̀-ͯ]/g;

// Collapse anything that isn't a letter or digit into a single space so
// punctuation never blocks a match ("re:zero" matches "re zero").
const NON_ALPHANUMERIC = /[^\p{L}\p{N}]+/gu;

/**
 * Normalize text for searching: lowercase, fold ё→е, drop diacritics, and
 * reduce punctuation/whitespace runs to single spaces. Returns a trimmed
 * string safe to substring-match against.
 */
function normalizeSearchText(value: string): string {
	return value
		.normalize('NFD')
		.replace(COMBINING_MARKS, '')
		.toLowerCase()
		.replace(NON_ALPHANUMERIC, ' ')
		.trim();
}

/**
 * Split a raw query into normalized search tokens. Empty query → no tokens,
 * which the index treats as "match everything".
 */
function tokenizeQuery(query: string): string[] {
	const normalized = normalizeSearchText(query);
	return normalized.length === 0 ? [] : normalized.split(' ');
}

type SearchFields = Array<string | number | null | undefined>;

/** One normalized string per non-empty field, ready to substring-match against. */
function buildHaystacks(fields: SearchFields): string[] {
	return fields
		.filter((field) => field !== null && field !== undefined)
		.map((field) => normalizeSearchText(String(field)));
}

export type SearchIndex<T> = {
	/**
	 * The matching items, in their original order. An item matches when every
	 * query token appears as a substring of one of its fields. AND-matching
	 * across tokens lets users type words in any order ("наруто опенинг" matches
	 * "Опенинг: Наруто"); each field is matched independently, so one token may
	 * hit the title and another the nomination. An empty query matches everything.
	 */
	filter(query: string): T[];
};

/**
 * Pre-normalize a list once so filtering it stays cheap.
 *
 * Normalizing is the expensive half of a match — NFD decomposition plus two
 * regex passes per field — and a search box re-filters the whole list on every
 * keypress. Doing it per item here instead of per item *per keystroke* takes a
 * ~400-event schedule from ~2ms to ~0.04ms per keypress, which matters because
 * the schedule page rebuilds its block/nomination grouping from the result.
 *
 * The index captures `items` as they are; rebuild it (a `$derived` on the list)
 * whenever the list itself changes.
 */
export function createSearchIndex<T>(
	items: readonly T[],
	getFields: (item: T) => SearchFields
): SearchIndex<T> {
	const entries = items.map((item) => ({ item, haystacks: buildHaystacks(getFields(item)) }));

	return {
		filter(query) {
			const tokens = tokenizeQuery(query);
			if (tokens.length === 0) return [...items];

			return entries
				.filter((entry) =>
					tokens.every((token) => entry.haystacks.some((haystack) => haystack.includes(token)))
				)
				.map((entry) => entry.item);
		}
	};
}
