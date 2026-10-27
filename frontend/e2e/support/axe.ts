import type { Page, TestInfo } from '@playwright/test';

import AxeBuilder from '@axe-core/playwright';
import { expect } from '@playwright/test';

type AxeResults = Awaited<ReturnType<AxeBuilder['analyze']>>;
type NodeResult = AxeResults['incomplete'][number]['nodes'][number];

const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22a', 'wcag22aa'];

const NOT_A_CONTRAST_QUESTION = new Set(['nonBmp', 'shortTextContent', 'equalRatio']);

const CHECKED_BY_HAND_ON_EVERY_PAGE = ['[data-bottom-nav]'];

export interface AccessibleOptions {
	builder?: AxeBuilder;
	contrastCheckedByHand?: string[];
}

export function axeBuilder(page: Page): AxeBuilder {
	return new AxeBuilder({ page }).withTags(WCAG_TAGS);
}

function contrastReason(node: NodeResult): string | undefined {
	const data = node.any[0]?.data as { messageKey?: string } | null | undefined;
	return data?.messageKey;
}

async function isInsideAny(page: Page, node: NodeResult, selectors: string[]): Promise<boolean> {
	if (selectors.length === 0) return false;
	const target = String(node.target[0]);
	return page.evaluate(
		({ target, selectors }) => {
			const element = document.querySelector(target);
			return selectors.some((selector) => element?.closest(selector) != null);
		},
		{ target, selectors }
	);
}

interface ContrastSplit {
	undecided: NodeResult[];
	checkedByHand: NodeResult[];
}

async function splitUndecidedContrast(
	page: Page,
	results: AxeResults,
	checkedByHandSelectors: string[]
): Promise<ContrastSplit> {
	const nodes = results.incomplete
		.filter((result) => result.id === 'color-contrast')
		.flatMap((result) => result.nodes);

	const split: ContrastSplit = { undecided: [], checkedByHand: [] };
	for (const node of nodes) {
		const reason = contrastReason(node);
		if (reason && NOT_A_CONTRAST_QUESTION.has(reason)) continue;
		if (await isInsideAny(page, node, checkedByHandSelectors)) {
			split.checkedByHand.push(node);
		} else {
			split.undecided.push(node);
		}
	}
	return split;
}

export async function expectAccessible(
	page: Page,
	testInfo: TestInfo,
	{ builder = axeBuilder(page), contrastCheckedByHand = [] }: AccessibleOptions = {}
): Promise<void> {
	const results = await builder.analyze();
	await testInfo.attach('axe-results', {
		body: JSON.stringify(results, null, 2),
		contentType: 'application/json'
	});

	expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);

	const { undecided, checkedByHand } = await splitUndecidedContrast(page, results, [
		...CHECKED_BY_HAND_ON_EVERY_PAGE,
		...contrastCheckedByHand
	]);
	expect(
		undecided.map((node) => ({ target: node.target, reason: contrastReason(node) })),
		'axe could not decide the contrast of these elements'
	).toEqual([]);

	if (checkedByHand.length > 0) {
		testInfo.annotations.push({
			type: 'contrast checked by hand',
			description: checkedByHand.map((node) => String(node.target[0])).join(', ')
		});
	}
}
