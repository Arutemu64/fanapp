<script lang="ts">
	import type { Component } from 'svelte';

	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import {
		Bell,
		BellRing,
		CalendarClock,
		ChevronRight,
		Coins,
		Megaphone,
		MessageCircle
	} from '@lucide/svelte';

	import type { NotificationDto, NotificationType } from '#lib/api/generated/index.js';

	import { minuteClock } from '#lib/services/minuteClock.js';
	import { formatRelativeTime } from '#lib/utils/formatters.js';
	import { toAppPath } from '#lib/utils/nav.js';

	interface Props {
		notification: NotificationDto;
		compact?: boolean;
	}

	let { notification, compact = false }: Props = $props();

	const TYPE_ICONS: Record<NotificationType, Component<{ class?: string }>> = {
		default: Bell,
		test: Bell,
		schedule_change: CalendarClock,
		schedule_subscription: BellRing,
		message: MessageCircle,
		points_received: Coins,
		broadcast: Megaphone
	};

	let Icon = $derived(TYPE_ICONS[notification.type] ?? Bell);
	let isNew = $derived(!notification.seen_at);
	let createdAt = $derived(formatRelativeTime(notification.created_at, minuteClock.now));

	// Backend-provided in-app deep-link (e.g. "/schedule"). Without one the item is
	// not clickable — and neither is one pointing at the screen already open
	// (organizer mailings link to the feed itself), where a tap would do nothing.
	let href = $derived.by(() => {
		if (!notification.path) return undefined;
		const target = resolve(toAppPath(notification.path));
		if (target === page.url.pathname) return undefined;
		return target;
	});
</script>

<!-- The title carries the link and its ::after stretches over the whole item
	(Inclusive Components "Cards"), instead of wrapping the item in an <a>: the
	body is organizer HTML that may contain its own links, and a link inside a
	link is invalid HTML. Body links sit above the stretched area via `relative`,
	since they come later in source order. -->
<div
	class={[
		'relative flex items-start gap-3 text-left',
		compact ? 'p-3' : 'rounded-xl border border-border bg-card p-4 shadow-sm',
		href && 'transition-colors',
		href && compact && 'hover:bg-accent',
		href && !compact && 'hover:bg-accent/50'
	]}
>
	<div class="relative shrink-0" aria-hidden="true">
		<div
			class="flex size-10 items-center justify-center rounded-full bg-muted text-muted-foreground"
		>
			<Icon class="size-5" />
		</div>
		{#if isNew}
			<span class="absolute top-0 right-0 size-2.5 rounded-full bg-primary ring-2 ring-card"></span>
		{/if}
	</div>

	<div class="min-w-0 flex-1">
		<p class="text-sm font-semibold text-foreground">
			{#if href}
				<a
					{href}
					class={[
						'outline-none after:absolute after:inset-0 focus-visible:after:ring-2 focus-visible:after:ring-ring focus-visible:after:ring-inset',
						!compact && 'after:rounded-xl'
					]}
				>
					{@render title()}
				</a>
			{:else}
				{@render title()}
			{/if}
		</p>
		{#if notification.body}
			<!-- Body is sanitized to a safe HTML subset on the backend (HtmlSanitizer). -->
			<!-- eslint-disable svelte/no-at-html-tags -->
			<div
				class="mt-0.5 text-sm whitespace-pre-line text-foreground/80 [&_a]:relative [&_a]:underline [&_a]:underline-offset-2"
			>
				{@html notification.body}
			</div>
			<!-- eslint-enable svelte/no-at-html-tags -->
		{/if}
		<time datetime={notification.created_at} class="mt-1 block text-xs text-primary">
			{createdAt}
		</time>
	</div>

	{#if href}
		<ChevronRight class="mt-2.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
	{/if}
</div>

{#snippet title()}
	<!-- The unseen dot is visual only; this gives screen readers the same cue. -->
	{#if isNew}
		<span class="sr-only">Новое:</span>
	{/if}
	{notification.title}
{/snippet}
