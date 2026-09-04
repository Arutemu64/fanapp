<script lang="ts">
	import type { Pathname } from '$app/types';
	import type { NotificationDTO } from '$lib/types/notifications';

	import { resolve } from '$app/paths';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import { Bell } from '@lucide/svelte';

	interface Props {
		notification: NotificationDTO;
		compact?: boolean;
	}

	let { notification, compact = false }: Props = $props();

	let createdAt = $derived(formatRelativeTime(notification.created_at));

	// Backend-provided in-app deep-link (e.g. "/schedule"). When absent the item
	// is not clickable. The path is a trusted internal route, so cast to Pathname.
	let path = $derived(notification.path ? (notification.path as Pathname) : undefined);

	let cardClass =
		'flex max-w-none flex-row items-start gap-3 rounded-xl border border-border bg-card p-4 text-left shadow-sm transition-colors hover:bg-accent/50';
</script>

{#snippet content()}
	<div class="relative shrink-0">
		<div
			class="flex h-10 w-10 items-center justify-center rounded-full bg-muted text-muted-foreground"
		>
			<Bell class="h-5 w-5" />
		</div>
		{#if !notification.seen_at}
			<span class="absolute top-0 right-0 h-2.5 w-2.5 rounded-full bg-primary ring-2 ring-card"
			></span>
		{/if}
	</div>
	<div class="min-w-0 flex-1">
		<div class="text-sm font-semibold text-foreground">{notification.title}</div>
		<div class="mt-0.5 text-xs text-muted-foreground">
			{#if notification.body}
				<!-- Body is sanitized to a safe HTML subset on the backend (HtmlSanitizer). -->
				<!-- eslint-disable-next-line svelte/no-at-html-tags -->
				<div class="mt-0.5 whitespace-pre-line text-foreground/80">{@html notification.body}</div>
			{/if}
		</div>
		<div class="text-xs text-primary">
			{createdAt}
		</div>
	</div>
{/snippet}

{#if compact}
	{#if path}
		<a
			href={resolve(path)}
			class="flex items-start gap-3 p-3 text-left transition-colors hover:bg-accent"
		>
			{@render content()}
		</a>
	{:else}
		<div class="flex items-start gap-3 p-3 text-left">
			{@render content()}
		</div>
	{/if}
{:else if path}
	<a href={resolve(path)} class={cardClass}>
		{@render content()}
	</a>
{:else}
	<div class={cardClass}>
		{@render content()}
	</div>
{/if}
