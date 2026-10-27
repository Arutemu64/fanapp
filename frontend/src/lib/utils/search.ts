const COMBINING_MARKS = /[̀-ͯ]/g;

const NON_ALPHANUMERIC = /[^\p{L}\p{N}]+/gu;

function normalizeSearchText(value: string): string {
	return value
		.normalize('NFD')
		.replace(COMBINING_MARKS, '')
		.toLowerCase()
		.replace(NON_ALPHANUMERIC, ' ')
		.trim();
}

type SearchFields = (string | number | null | undefined)[];

export interface SearchIndex<T> {
	filter: (query: string) => T[];
}

export function createSearchIndex<T>(
	items: readonly T[],
	getFields: (item: T) => SearchFields
): SearchIndex<T> {
	const entries = items.map((item) => {
		const haystacks = getFields(item)
			.filter((field) => field !== null && field !== undefined)
			.map((field) => normalizeSearchText(String(field)));
		return { item, haystacks };
	});

	return {
		filter(query) {
			const normalized = normalizeSearchText(query);
			if (normalized.length === 0) return [...items];
			const tokens = normalized.split(' ');

			const matches: T[] = [];
			for (const { item, haystacks } of entries) {
				const matchesAll = tokens.every((token) =>
					haystacks.some((haystack) => haystack.includes(token))
				);
				if (matchesAll) {
					matches.push(item);
				}
			}
			return matches;
		}
	};
}
