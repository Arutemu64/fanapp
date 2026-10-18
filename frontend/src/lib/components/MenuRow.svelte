<script lang="ts">
	import type { Path } from '$app/types';
	import type { Component } from 'svelte';

	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import ExternalLink from '@lucide/svelte/icons/external-link';

	import * as Item from '#lib/components/ui/item/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { resolvePath } from '#lib/utils/paths.js';

	// One row shape for every grouped menu (the /profile and Гид hubs, the toolbox,
	// Home's get-ready list), so a row leads somewhere or does something the same
	// way wherever it sits. The target is one of three, never a mix.
	type Target =
		| { href: Path; externalHref?: never; onclick?: never }
		| {
				/** A URL outside the app (a web page, mailto:). */
				externalHref: string;
				/** Opens a new tab, marked with an external-link icon; mailto: stays put. */
				newTab: boolean;
				href?: never;
				onclick?: never;
		  }
		| { onclick: () => void; href?: never; externalHref?: never };

	type Props = Target & {
		label: string;
		/** A line under the label, for rows whose title alone doesn't say what is behind them. */
		description?: string;
		/** Shows the whole description instead of clamping it to two lines. */
		fullDescription?: boolean;
		icon: Component;
		/** 'primary' tints the icon tile for a row that asks to be acted on. */
		tone?: 'muted' | 'primary';
		/** Current state shown before the chevron, so it reads without opening the page. */
		value?: string;
		/**
		 * The drill-in chevron. On by default for an in-app link; an action row
		 * takes it only when it sits among link rows that all carry one.
		 */
		chevron?: boolean;
	};

	let props: Props = $props();

	let Icon = $derived(props.icon);
	let showChevron = $derived(props.chevron ?? props.href !== undefined);
	let opensNewTab = $derived(props.externalHref !== undefined && props.newTab);
</script>

{#snippet body()}
	<Item.Media
		class={[
			'size-9 rounded-lg',
			props.tone === 'primary'
				? 'bg-primary/10 text-primary-700 dark:text-primary'
				: 'bg-muted text-muted-foreground'
		]}
	>
		<Icon class="size-5" aria-hidden="true" />
	</Item.Media>
	<Item.Content>
		<Item.Title class="text-base">{props.label}</Item.Title>
		{#if props.description}
			<Item.Description class={[props.fullDescription && 'line-clamp-none']}>
				{props.description}
			</Item.Description>
		{/if}
	</Item.Content>
	{#if props.value || showChevron || opensNewTab}
		<Item.Actions>
			{#if props.value}
				<span class="text-sm text-muted-foreground">{props.value}</span>
			{/if}
			{#if opensNewTab}
				<ExternalLink class="size-4 text-muted-foreground" aria-hidden="true" />
				<span class="sr-only">({m.guide_opens_in_new_tab()})</span>
			{:else if showChevron}
				<ChevronRight class="size-4 text-muted-foreground" aria-hidden="true" />
			{/if}
		</Item.Actions>
	{/if}
{/snippet}

<Item.Root class="rounded-none">
	{#snippet child({ props: itemProps })}
		{#if props.href !== undefined}
			<a href={resolvePath(props.href)} {...itemProps}>
				{@render body()}
			</a>
		{:else if props.externalHref !== undefined}
			<a
				href={props.externalHref}
				target={props.newTab ? '_blank' : undefined}
				rel={props.newTab ? 'noopener noreferrer' : undefined}
				{...itemProps}
			>
				{@render body()}
			</a>
		{:else}
			<button type="button" {...itemProps} onclick={props.onclick}>
				{@render body()}
			</button>
		{/if}
	{/snippet}
</Item.Root>
