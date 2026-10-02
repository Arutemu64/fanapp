import { describe, expect, it } from 'vitest';

import { isValidEmail, isValidOtp, normalizeEmail } from './validation';

describe('isValidEmail', () => {
	it.each([
		['user@example.com', true],
		['a.b+c@sub.example.ru', true],
		['', false],
		['   ', false],
		['user@', false],
		['@example.com', false],
		['user@example', false],
		['us er@example.com', false]
	])('%j -> %j', (value, expected) => {
		expect(isValidEmail(value)).toBe(expected);
	});
});

describe('normalizeEmail', () => {
	it('trims and lowercases', () => {
		expect(normalizeEmail('  User@Example.COM ')).toBe('user@example.com');
	});
});

describe('isValidOtp', () => {
	it.each([
		['123456', true],
		['000000', true],
		['', false],
		[' 123456', false],
		['12345', false],
		['1234567', false],
		['12345a', false]
	])('%j -> %j', (value, expected) => {
		expect(isValidOtp(value)).toBe(expected);
	});
});
