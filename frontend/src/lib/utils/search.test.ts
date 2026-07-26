import { describe, expect, it } from 'vitest';

import { createSearchIndex } from './search';

/** Index over bare titles — enough for the normalization rules. */
function titleIndex(titles: string[]) {
	return createSearchIndex(titles, (title) => [title]);
}

type ScheduleRow = {
	number: number;
	title: string;
	block_title: string | null;
	nomination_title: string | null;
};

// Mirrors the schedule page's field set: a number plus three text fields, two of
// which are nullable.
const rows: ScheduleRow[] = [
	{ number: 1, title: 'Опенинг: Наруто', block_title: 'Блок А', nomination_title: 'Караоке' },
	{ number: 2, title: 'Café Européen', block_title: null, nomination_title: null },
	{
		number: 12,
		title: 'Re:Zero — дефиле',
		block_title: 'Блок Б',
		nomination_title: 'Одиночное дефиле'
	},
	{ number: 3, title: 'Ёжик в тумане', block_title: 'Блок Б', nomination_title: 'Караоке' }
];

const rowIndex = createSearchIndex(rows, (row) => [
	row.number,
	row.title,
	row.block_title,
	row.nomination_title
]);

const matchedTitles = (query: string) => rowIndex.filter(query).map((row) => row.title);

describe('createSearchIndex', () => {
	it('returns every item for an empty or whitespace-only query', () => {
		expect(rowIndex.filter('')).toEqual(rows);
		expect(rowIndex.filter('   ')).toEqual(rows);
		// Punctuation alone normalizes away to nothing, so it is not a token either.
		expect(rowIndex.filter('—')).toEqual(rows);
	});

	it('matches regardless of case', () => {
		expect(titleIndex(['Наруто']).filter('НАРУТО')).toEqual(['Наруто']);
		expect(titleIndex(['НАРУТО']).filter('наруто')).toEqual(['НАРУТО']);
	});

	it('folds ё and е in both directions', () => {
		expect(titleIndex(['Ёжик']).filter('ежик')).toEqual(['Ёжик']);
		expect(titleIndex(['Ежик']).filter('ёжик')).toEqual(['Ежик']);
	});

	it('ignores diacritics', () => {
		expect(titleIndex(['Café']).filter('cafe')).toEqual(['Café']);
		expect(titleIndex(['Cafe']).filter('café')).toEqual(['Cafe']);
	});

	it('treats punctuation as a word break rather than a blocker', () => {
		expect(titleIndex(['Re:Zero']).filter('re zero')).toEqual(['Re:Zero']);
		expect(titleIndex(['Re:Zero']).filter('re:zero')).toEqual(['Re:Zero']);
		// The break is real: the two words never join into one token.
		expect(titleIndex(['Re:Zero']).filter('rezero')).toEqual([]);
	});

	it('requires every token to match, in any order', () => {
		expect(matchedTitles('наруто опенинг')).toEqual(['Опенинг: Наруто']);
		expect(matchedTitles('опенинг наруто')).toEqual(['Опенинг: Наруто']);
	});

	it('lets separate tokens match separate fields', () => {
		expect(matchedTitles('наруто караоке')).toEqual(['Опенинг: Наруто']);
	});

	it('matches numeric fields', () => {
		expect(matchedTitles('12')).toEqual(['Re:Zero — дефиле']);
	});

	it('ignores null and undefined fields', () => {
		expect(matchedTitles('cafe')).toEqual(['Café Européen']);

		const sparse = createSearchIndex([{ title: 'Тест' }], (item: { title: string }) => [
			item.title,
			null,
			undefined
		]);
		expect(sparse.filter('тест')).toEqual([{ title: 'Тест' }]);
	});

	it('keeps the original order of the items', () => {
		expect(matchedTitles('караоке')).toEqual(['Опенинг: Наруто', 'Ёжик в тумане']);
	});

	it('returns nothing when one token matches nothing', () => {
		expect(matchedTitles('наруто дефиле')).toEqual([]);
		expect(matchedTitles('такого нет')).toEqual([]);
	});

	it('does not hand out the source array', () => {
		const items = ['Наруто'];
		const result = titleIndex(items).filter('');

		expect(result).not.toBe(items);
		expect(result).toEqual(items);
	});
});
