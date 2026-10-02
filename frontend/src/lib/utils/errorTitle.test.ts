import { describe, expect, it } from 'vitest';

import { statusTitle } from './errorTitle';

describe('statusTitle', () => {
	it.each([
		[403, 'Доступ ограничен'],
		[404, 'Страница не найдена'],
		[500, 'Что-то пошло не так'],
		[418, 'Что-то пошло не так']
	])('%d -> %s', (status, expected) => {
		expect(statusTitle(status)).toBe(expected);
	});
});
