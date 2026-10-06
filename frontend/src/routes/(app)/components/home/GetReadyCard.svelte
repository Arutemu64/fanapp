<script lang="ts">
	import type { Pathname } from '$app/types';
	import type { Component } from 'svelte';

	import { resolve } from '$app/paths';
	import { ArrowRight } from '@lucide/svelte';

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
	const ICON = 'bg-primary/10 text-primary';
	const FEATURED_ICON = 'bg-primary/15 text-primary';

	const COMPACT =
		'group flex h-full flex-col rounded-2xl border border-border bg-card p-4 text-left shadow-sm transition-colors hover:border-primary-300 hover:bg-primary-50/40 dark:hover:border-primary-500 dark:hover:bg-primary-900/10';
	const FEATURED =
		'group flex items-center gap-4 rounded-2xl border border-primary-200 bg-primary-50 p-4 text-left shadow-sm transition-colors hover:bg-primary-100/70 sm:p-5 dark:border-primary-800/50 dark:bg-primary-900/20 dark:hover:bg-primary-900/30';

	let containerClass = $derived(featured ? FEATURED : COMPACT);
</script>

{#snippet compactBody()}
	<span class={['mb-3 flex h-11 w-11 items-center justify-center rounded-xl', ICON]}>
		<Icon class="h-5 w-5" aria-hidden="true" />
	</span>
	<h3 class="text-sm font-semibold text-foreground sm:text-base">
		{title}
	</h3>
	<p class="mt-1 text-xs leading-relaxed text-muted-foreground sm:text-sm">
		{description}
	</p>
	<span class="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary">
		{actionLabel}
		<!-- Arrow implies navigation; only show it for link cards, not action buttons -->
		{#if href}
			<ArrowRight
				class="size-3.5 transition-transform group-hover:translate-x-0.5"
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
		<Icon class="size-6 sm:size-7" aria-hidden="true" />
	</span>
	<div class="min-w-0 flex-1">
		<h3 class="text-base font-bold text-foreground sm:text-lg">
			{title}
		</h3>
		<p class="mt-1 text-sm leading-relaxed text-muted-foreground">
			{description}
		</p>
	</div>
	<span
		class="inline-flex shrink-0 items-center gap-1.5 self-center text-sm font-semibold text-primary"
	>
		<span class="hidden sm:inline">{actionLabel}</span>
		{#if href}
			<ArrowRight
				class="size-4 transition-transform group-hover:translate-x-0.5"
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
