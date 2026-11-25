<script lang="ts">
	import type { Path } from '$app/types';
	import type { Component } from 'svelte';

	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import ExternalLink from '@lucide/svelte/icons/external-link';

	import * as Item from '#lib/components/ui/item/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { resolvePath } from '#lib/utils/paths.js';

	type Target =
		| { href: Path; externalHref?: never; onclick?: never }
		| {
				externalHref: string;
				newTab: boolean;
				href?: never;
				onclick?: () => void;
		  }
		| { onclick: () => void; href?: never; externalHref?: never };

	type Props = Target & {
		label: string;
		description?: string;
		fullDescription?: boolean;
		icon: Component;
		variant?: 'card';
		tone?: 'muted' | 'primary';
		value?: string;
		chevron?: boolean;
	};

	let props: Props = $props();

	let Icon = $derived(props.icon);
	let isCard = $derived(props.variant === 'card');
	let showChevron = $derived(props.chevron ?? (!isCard && props.href !== undefined));
	let opensNewTab = $derived(props.externalHref !== undefined && props.newTab);
</script>

{#snippet body()}
	<Item.Media
		class={[
			'size-9 rounded-lg',
			isCard && 'max-sm:size-7',
			props.tone === 'primary'
				? 'bg-primary/10 text-primary-700 dark:text-primary'
				: 'bg-muted text-muted-foreground'
		]}
	>
		<Icon class="size-5" aria-hidden="true" />
	</Item.Media>
	<Item.Content class={isCard ? 'min-w-0 self-start max-sm:contents' : undefined}>
		<Item.Title class={isCard ? 'line-clamp-none wrap-anywhere' : 'text-base'}>
			{props.label}
		</Item.Title>
		{#if props.description}
			<Item.Description
				class={[
					(props.fullDescription || isCard) && 'line-clamp-none',
					isCard && 'max-sm:col-span-full max-sm:row-start-2'
				]}
			>
				{props.description}
			</Item.Description>
		{/if}
	</Item.Content>
	{#if props.value || showChevron || opensNewTab}
		<Item.Actions class={isCard ? 'max-sm:col-start-3 max-sm:row-start-1' : undefined}>
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

<Item.Root
	variant={isCard ? 'outline' : undefined}
	size={isCard ? 'sm' : undefined}
	class={isCard
		? 'h-full flex-nowrap rounded-2xl bg-card max-sm:grid max-sm:grid-cols-[auto_minmax(0,1fr)_auto] max-sm:gap-2'
		: 'rounded-none'}
>
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
				onclick={props.onclick}
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
