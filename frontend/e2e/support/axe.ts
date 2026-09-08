import type { Page } from '@playwright/test';

import AxeBuilder from '@axe-core/playwright';

// The WCAG levels we hold the app to. 2.0 A/AA plus 2.1 A/AA is the widely-adopted
// baseline (and what most legislation references); axe's `best-practice` tag is
// deliberately excluded so a spec fails on real conformance issues, not on
// stylistic hints. All rules within these tags are enforced — color-contrast
// included (the muted-text and active-nav token debt it caught is now fixed).
const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

/** A WCAG-scoped AxeBuilder for the page under test. */
export function axeBuilder(page: Page): AxeBuilder {
	return new AxeBuilder({ page }).withTags(WCAG_TAGS);
}
