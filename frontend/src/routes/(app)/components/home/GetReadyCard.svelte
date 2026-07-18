<script lang="ts">
	import type { Pathname } from '$app/types';
	import type { Component } from 'svelte';

	import { resolve } from '$app/paths';
	import { ArrowRightOutline } from 'flowbite-svelte-icons';

	interface Props {
		title: string;
		description: string;
		icon: Component;
		/** The primary next step: larger, horizontal, on a tinted surface. */
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
		featured = false,
		actionLabel = 'Открыть',
		href,
		onclick
	}: Props = $props();

	// One brand accent for every card: the cards share a voice, so scale and
	// position (featured first) carry the hierarchy, not a per-card color.
	const ICON = 'bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400';
	const FEATURED_ICON =
		'bg-primary-100 text-primary-700 dark:bg-primary-900/40 dark:text-primary-300';

	const COMPACT =
		'group flex h-full flex-col rounded-2xl border border-gray-200 bg-white p-4 text-left shadow-sm transition-colors hover:border-primary-300 hover:bg-primary-50/40 dark:border-gray-800 dark:bg-gray-900 dark:hover:border-primary-500 dark:hover:bg-primary-900/10';
	const FEATURED =
		'group flex items-center gap-4 rounded-2xl border border-primary-200 bg-primary-50 p-4 text-left shadow-sm transition-colors hover:bg-primary-100/70 sm:p-5 dark:border-primary-800/50 dark:bg-primary-900/20 dark:hover:bg-primary-900/30';

	let containerClass = $derived(featured ? FEATURED : COMPACT);
</script>

{#snippet compactBody()}
	<span class={['mb-3 flex h-11 w-11 items-center justify-center rounded-xl', ICON]}>
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
			'flex h-12 w-12 shrink-0 items-center justify-center rounded-xl sm:h-14 sm:w-14',
			FEATURED_ICON
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
