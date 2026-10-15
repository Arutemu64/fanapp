import type { Component } from 'svelte';

import { Drama, Gamepad2, Palette, Store, Tent, Trophy } from '@lucide/svelte';

export interface GuideArticle {
	slug: string;
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
}

const ICONS = {
	stage: Drama,
	fair: Store,
	authors: Palette,
	stands: Tent,
	contests: Trophy,
	play: Gamepad2
};

// Eager, so every article ships in the main bundle and opens offline with the
// rest of the guide; the set is a handful of short pages. mdsvex exposes each
// file's frontmatter as `metadata` next to the compiled component.
const modules = import.meta.glob<{ default: Component; metadata: Frontmatter }>(
	'/src/content/guide/*.md',
	{ eager: true }
);

export const guideArticles: GuideArticle[] = Object.entries(modules)
	.map(([path, module]) => ({
		order: module.metadata.order,
		article: {
			slug: path.split('/').pop()?.replace(/\.md$/, '') ?? path,
			title: module.metadata.title,
			description: module.metadata.description,
			icon: ICONS[module.metadata.icon],
			Content: module.default
		}
	}))
	.sort((a, b) => a.order - b.order)
	.map(({ article }) => article);
