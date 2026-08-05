<script lang="ts">
	import type { Pathname } from '$app/types';
	import type { NotificationDTO } from '$lib/types/notifications';

	import { resolve } from '$app/paths';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import { Card, DropdownItem } from 'flowbite-svelte';
	import { BellSolid } from 'flowbite-svelte-icons';

	interface Props {
		notification: NotificationDTO;
		compact?: boolean;
	}

	let { notification, compact = false }: Props = $props();

	let createdAt = $derived(formatRelativeTime(notification.created_at));

	// Backend-provided in-app deep-link (e.g. "/schedule"). When absent the item
	// is not clickable. The path is a trusted internal route, so cast to Pathname.
	let href = $derived(notification.path ? resolve(notification.path as Pathname) : undefined);

	// Flowbite Card supplies the border + surface + dark variants. flex-row overrides
	// Card's default flex-col so the icon sits beside the text; shadow-sm is the one
	// sanctioned resting shadow for a standalone tappable list item (DESIGN,
	// Border-Before-Shadow) and overrides Card's shadow-md default via tailwind-merge.
	let cardClass = 'flex max-w-none flex-row items-start gap-3 rounded-xl p-4 text-left shadow-sm';
</script>

{#snippet content()}
	<div class="relative shrink-0">
		<div
			class="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400"
		>
			<BellSolid class="h-5 w-5" />
		</div>
		{#if !notification.seen_at}
			<div
				class="absolute -end-0.5 -top-0.5 inline-flex h-3 w-3 rounded-full border-2 border-white bg-primary-600 dark:border-gray-900 dark:bg-primary-500"
			></div>
		{/if}
	</div>
	<div class="w-full min-w-0">
		<div class="mb-1.5 text-sm whitespace-normal text-gray-500 dark:text-gray-400">
			<span class="font-semibold text-gray-900 dark:text-white">{notification.title}</span>
			{#if notification.body}
				<!-- Body is sanitized to a safe HTML subset on the backend (HtmlSanitizer). -->
				<!-- eslint-disable-next-line svelte/no-at-html-tags -->
				<div class="mt-0.5 whitespace-pre-line">{@html notification.body}</div>
			{/if}
		</div>
		<div class="text-xs text-primary-600 dark:text-primary-400">
			{createdAt}
		</div>
	</div>
{/snippet}

{#if compact}
	<!-- DropdownItem renders an <a> when given an href, so the whole row deep-links. -->
	<DropdownItem {href} class="flex items-start gap-3 text-left">
		{@render content()}
	</DropdownItem>
{:else if href}
	<!-- Card renders an <a> here, so the whole row deep-links. Branching on href
		(rather than passing it optionally) narrows Card's href-vs-div prop union. -->
	<Card {href} class={cardClass}>
		{@render content()}
	</Card>
{:else}
	<Card class={cardClass}>
		{@render content()}
	</Card>
{/if}
