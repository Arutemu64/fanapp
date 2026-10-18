import type { Page } from '@playwright/test';

import AxeBuilder from '@axe-core/playwright';

// The WCAG levels we hold the app to. 2.0 A/AA plus 2.1 A/AA is the widely-adopted
// baseline (and what most legislation references); axe's `best-practice` tag is
// deliberately excluded so a spec fails on real conformance issues, not on
// stylistic hints. All rules within these tags are enforced, color-contrast
// included.
const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

// The two best-practice rules held on top: every screen names itself with one
// <h1> (the navbar renders `page.data.title` as it, so a page or error boundary
// without a title has none) and headings don't skip a level. axe runs a rule
// outside `runOnly`'s tags when `rules` enables it by id:
// https://github.com/dequelabs/axe-core/blob/develop/doc/API.md#options-parameter
const EXTRA_RULES = ['page-has-heading-one', 'heading-order'];

/**
 * A WCAG-scoped AxeBuilder for the page under test. Set through `options()`
 * because `withTags()` and `withRules()` each replace `runOnly`. AxeBuilder's
 * `disableRules()` replaces `rules` too, dropping EXTRA_RULES; relax a rule by
 * narrowing the scan with `.include()` / `.exclude()` instead.
 */
export function axeBuilder(page: Page): AxeBuilder {
	const rules = Object.fromEntries(EXTRA_RULES.map((id) => [id, { enabled: true }]));
	return new AxeBuilder({ page }).options({
		runOnly: { type: 'tag', values: WCAG_TAGS },
		rules
	});
}
