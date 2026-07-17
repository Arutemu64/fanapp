<script module lang="ts">
	// Accent name drives the card's color family; the full class strings live in
	// ACCENTS below so Tailwind can statically see every utility.
	export type ReadyAccent = 'primary' | 'secondary' | 'amber' | 'green' | 'blue';
</script>

<script lang="ts">
	import type { Pathname } from '$app/types';
	import type { Component } from 'svelte';

	import { resolve } from '$app/paths';
	import { ArrowRightOutline } from 'flowbite-svelte-icons';

	interface Props {
		title: string;
		description: string;
		icon: Component;
		accent: ReadyAccent;
		/** The primary next step: larger, horizontal, on an accent-tinted surface. */
		featured?: boolean;
		/** Action text shown at the bottom of the card. */
		actionLabel?: string;
		href?: Pathname;
		onclick?: () => void;
	}

	let {
		title,
		description,
		icon: Icon,
		accent,
		featured = false,
		actionLabel = 'Открыть',
		href,
		onclick
	}: Props = $props();

	// Full class strings per accent (static, so Tailwind keeps them in the build).
	const ACCENTS: Record<
		ReadyAccent,
		{ icon: string; hover: string; surface: string; featuredIcon: string }
	> = {
		primary: {
			icon: 'bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400',
			hover:
				'hover:border-primary-300 hover:bg-primary-50/40 dark:hover:border-primary-500 dark:hover:bg-primary-900/10',
			surface:
				'border-primary-200 bg-primary-50 hover:bg-primary-100/70 dark:border-primary-800/50 dark:bg-primary-900/20 dark:hover:bg-primary-900/30',
			featuredIcon: 'bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300'
		},
		secondary: {
			icon: 'bg-secondary-50 text-secondary-600 dark:bg-secondary-900/30 dark:text-secondary-400',
			hover:
				'hover:border-secondary-300 hover:bg-secondary-50/40 dark:hover:border-secondary-500 dark:hover:bg-secondary-900/10',
			surface:
				'border-secondary-200 bg-secondary-50 hover:bg-secondary-100/70 dark:border-secondary-800/50 dark:bg-secondary-900/20 dark:hover:bg-secondary-900/30',
			featuredIcon:
				'bg-secondary-100 text-secondary-700 dark:bg-secondary-900/40 dark:text-secondary-300'
		},
		amber: {
			icon: 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
			hover:
				'hover:border-amber-300 hover:bg-amber-50/40 dark:hover:border-amber-500 dark:hover:bg-amber-900/10',
			surface:
				'border-amber-200 bg-amber-50 hover:bg-amber-100/70 dark:border-amber-800/50 dark:bg-amber-900/20 dark:hover:bg-amber-900/30',
			featuredIcon: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
		},
		green: {
			icon: 'bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400',
			hover:
				'hover:border-green-300 hover:bg-green-50/40 dark:hover:border-green-500 dark:hover:bg-green-900/10',
			surface:
				'border-green-200 bg-green-50 hover:bg-green-100/70 dark:border-green-800/50 dark:bg-green-900/20 dark:hover:bg-green-900/30',
			featuredIcon: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
		},
		blue: {
			icon: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
			hover:
				'hover:border-blue-300 hover:bg-blue-50/40 dark:hover:border-blue-500 dark:hover:bg-blue-900/10',
			surface:
				'border-blue-200 bg-blue-50 hover:bg-blue-100/70 dark:border-blue-800/50 dark:bg-blue-900/20 dark:hover:bg-blue-900/30',
			featuredIcon: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
		}
	};

	let theme = $derived(ACCENTS[accent]);

	const COMPACT =
		'group flex h-full flex-col rounded-2xl border border-gray-200 bg-white p-4 text-left shadow-sm transition-colors dark:border-gray-800 dark:bg-gray-900';
	const FEATURED =
		'group flex items-center gap-4 rounded-2xl border p-4 text-left shadow-sm transition-colors sm:p-5';

	let containerClass = $derived(featured ? [FEATURED, theme.surface] : [COMPACT, theme.hover]);
</script>

{#snippet compactBody()}
	<span
		class={[
			'mb-3 flex h-11 w-11 items-center justify-center rounded-xl transition-transform group-hover:scale-105',
			theme.icon
		]}
	>
		<Icon class="h-5 w-5" aria-hidden="true" />
	</span>
	<h3 class="text-sm font-semibold text-gray-900 sm:text-base dark:text-white">
		{title}
	</h3>
	<p class="mt-1 text-xs leading-relaxed text-gray-600 sm:text-sm dark:text-gray-400">
		{description}
	</p>
	<span
		class="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary-600 dark:text-primary-400"
	>
		{actionLabel}
		<!-- Arrow implies navigation; only show it for link cards, not action buttons -->
		{#if href}
			<ArrowRightOutline
				class="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5"
				aria-hidden="true"
			/>
		{/if}
	</span>
{/snippet}

{#snippet featuredBody()}
	<span
		class={[
			'flex h-12 w-12 shrink-0 items-center justify-center rounded-xl transition-transform group-hover:scale-105 sm:h-14 sm:w-14',
			theme.featuredIcon
		]}
	>
		<Icon class="h-6 w-6 sm:h-7 sm:w-7" aria-hidden="true" />
	</span>
	<div class="min-w-0 flex-1">
		<h3 class="text-base font-bold text-gray-900 sm:text-lg dark:text-white">
			{title}
		</h3>
		<p class="mt-1 text-sm leading-relaxed text-gray-600 dark:text-gray-300">
			{description}
		</p>
	</div>
	<span
		class="inline-flex shrink-0 items-center gap-1.5 self-center text-sm font-semibold text-primary-600 dark:text-primary-400"
	>
		<span class="hidden sm:inline">{actionLabel}</span>
		{#if href}
			<ArrowRightOutline
				class="h-4 w-4 transition-transform group-hover:translate-x-0.5"
				aria-hidden="true"
			/>
		{/if}
	</span>
{/snippet}

{#snippet body()}
	{#if featured}{@render featuredBody()}{:else}{@render compactBody()}{/if}
{/snippet}

{#if href}
	<a href={resolve(href)} class={containerClass}>
		{@render body()}
	</a>
{:else}
	<button type="button" {onclick} class={containerClass}>
		{@render body()}
	</button>
{/if}
