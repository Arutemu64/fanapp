import type { Page, TestInfo } from '@playwright/test';

import AxeBuilder from '@axe-core/playwright';
import { expect } from '@playwright/test';

// axe-core's own types, reached through the builder: pnpm keeps axe-core a
// transitive dependency, so it can't be imported by name from here.
type AxeResults = Awaited<ReturnType<AxeBuilder['analyze']>>;
type NodeResult = AxeResults['incomplete'][number]['nodes'][number];

// The WCAG levels we hold the app to: 2.0, 2.1 and 2.2 at A/AA. axe leaves its
// 2.2 rules (target-size among them) off unless their tags are named. axe's
// `best-practice` tag is deliberately excluded so a spec fails on real
// conformance issues, not on stylistic hints. All rules within these tags are
// enforced, color-contrast included.
// https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md
const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22a', 'wcag22aa'];

// Reasons axe gives for an undecided contrast check that are not a contrast
// question at all: a glyph-only string (a "•••" separator), text too short to
// call text, or text painted in its own background colour, which is how an
// input that is deliberately invisible (the code field's overlay) looks.
// The keys are axe-core's `color-contrast` incomplete messages (locales/_template.json).
const NOT_A_CONTRAST_QUESTION = new Set(['nonBmp', 'shortTextContent', 'equalRatio']);

export interface AccessibleOptions {
	builder?: AxeBuilder;
	// Selectors of regions whose contrast axe can't measure (text over a photo)
	// and a human has checked. Their undecided contrast is noted in the report
	// instead of failing the test.
	contrastCheckedByHand?: string[];
}

/** A WCAG-scoped AxeBuilder for the page under test. */
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

async function undecidedContrast(
	page: Page,
	results: AxeResults,
	checkedByHand: string[]
): Promise<NodeResult[]> {
	const nodes = results.incomplete
		.filter((result) => result.id === 'color-contrast')
		.flatMap((result) => result.nodes);

	const undecided: NodeResult[] = [];
	for (const node of nodes) {
		const reason = contrastReason(node);
		if (reason && NOT_A_CONTRAST_QUESTION.has(reason)) continue;
		if (await isInsideAny(page, node, checkedByHand)) continue;
		undecided.push(node);
	}
	return undecided;
}

/**
 * Scan the page, attach the full results to the report, and fail on any
 * violation or on a contrast check axe could not decide.
 */
export async function expectAccessible(
	page: Page,
	testInfo: TestInfo,
	{ builder = axeBuilder(page), contrastCheckedByHand = [] }: AccessibleOptions = {}
): Promise<void> {
	const results = await builder.analyze();
	// Passes and inconclusive checks are in the full results too, which the
	// violations list alone can't explain. https://playwright.dev/docs/accessibility-testing
	await testInfo.attach('axe-results', {
		body: JSON.stringify(results, null, 2),
		contentType: 'application/json'
	});

	expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);

	// axe files contrast it can't measure (a gradient, a background image, text
	// over another element) under `incomplete`, not `violations`, so it would pass
	// unseen. Fail on it so a human decides: fix the surface, or check it by hand
	// and list it in `contrastCheckedByHand`.
	const undecided = await undecidedContrast(page, results, contrastCheckedByHand);
	expect(
		undecided.map((node) => ({ target: node.target, reason: contrastReason(node) })),
		'axe could not decide the contrast of these elements'
	).toEqual([]);

	if (contrastCheckedByHand.length > 0) {
		testInfo.annotations.push({
			type: 'contrast checked by hand',
			description: contrastCheckedByHand.join(', ')
		});
	}
}
