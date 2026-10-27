import type { Component } from 'svelte';

import Drama from '@lucide/svelte/icons/drama';
import Gamepad2 from '@lucide/svelte/icons/gamepad-2';
import Palette from '@lucide/svelte/icons/palette';
import ShieldCheck from '@lucide/svelte/icons/shield-check';
import Store from '@lucide/svelte/icons/store';
import Tent from '@lucide/svelte/icons/tent';
import Trophy from '@lucide/svelte/icons/trophy';

export type GuideSection = 'important' | 'activities';

export interface GuideArticle {
	slug: string;
	section: GuideSection;
	title: string;
	description: string;
	icon: Component;
	Content: Component;
}

interface Frontmatter {
	title: string;
	description: string;
	icon: keyof typeof ICONS;
	order: number;
	section?: GuideSection;
}

const ICONS = {
	entry: ShieldCheck,
	stage: Drama,
	fair: Store,
	authors: Palette,
	stands: Tent,
	contests: Trophy,
	play: Gamepad2
};

const modules = import.meta.glob<{ default: Component; metadata: Frontmatter }>(
	'/src/content/guide/*.md',
	{ eager: true }
);

export const guideArticles: GuideArticle[] = Object.entries(modules)
	.map(([path, module]) => ({
		order: module.metadata.order,
		article: {
			slug: path.split('/').pop()?.replace(/\.md$/, '') ?? path,
			section: module.metadata.section ?? 'activities',
			title: module.metadata.title,
			description: module.metadata.description,
			icon: ICONS[module.metadata.icon],
			Content: module.default
		}
	}))
	.sort((a, b) => a.order - b.order)
	.map(({ article }) => article);
