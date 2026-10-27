<script lang="ts">
	import type { Component } from 'svelte';

	import { page } from '$app/state';
	import Bell from '@lucide/svelte/icons/bell';
	import BellRing from '@lucide/svelte/icons/bell-ring';
	import CalendarClock from '@lucide/svelte/icons/calendar-clock';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Coins from '@lucide/svelte/icons/coins';
	import Megaphone from '@lucide/svelte/icons/megaphone';
	import MessageCircle from '@lucide/svelte/icons/message-circle';

	import type { NotificationDto, NotificationType } from '#lib/api/generated/index.js';

	import { m } from '#lib/paraglide/messages.js';
	import { minuteClock } from '#lib/services/minuteClock.js';
	import { formatRelativeTime } from '#lib/utils/formatters.js';
	import { toAppPath } from '#lib/utils/nav.js';
	import { resolvePath } from '#lib/utils/paths.js';

	interface Props {
		notification: NotificationDto;
		isNew: boolean;
	}

	let { notification, isNew }: Props = $props();

	const TYPE_ICONS: Partial<Record<string, Component<{ class?: string }>>> = {
		default: Bell,
		test: Bell,
		schedule_change: CalendarClock,
		schedule_subscription: BellRing,
		message: MessageCircle,
		quest: Coins,
		broadcast: Megaphone
	} satisfies Record<NotificationType, Component<{ class?: string }>>;

	let Icon = $derived(TYPE_ICONS[notification.type] ?? Bell);
	let createdAt = $derived(formatRelativeTime(notification.created_at, minuteClock.now));

	let href = $derived.by(() => {
		if (!notification.path) return undefined;
		const target = resolvePath(toAppPath(notification.path));
		if (target === page.url.pathname) return undefined;
		return target;
	});
</script>

<div
	class={[
		'relative flex items-start gap-3 rounded-xl border border-border bg-card p-4 text-left shadow-sm',
		href && 'transition-colors hover:bg-accent/50'
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
		<p class="text-base font-semibold text-foreground">
			{#if href}
				<a
					{href}
					class="outline-none after:absolute after:inset-0 after:rounded-xl focus-visible:after:ring-2 focus-visible:after:ring-ring focus-visible:after:ring-inset"
				>
					{@render title()}
				</a>
			{:else}
				{@render title()}
			{/if}
		</p>
		{#if notification.body}
			<!-- eslint-disable svelte/no-at-html-tags -- body is sanitized to a safe HTML subset on the backend (HtmlSanitizer) -->
			<div
				class="mt-0.5 text-body whitespace-pre-line text-foreground/80 [&_a]:relative [&_a]:underline [&_a]:underline-offset-2"
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
	{#if isNew}
		<span class="sr-only">{m.notification_new_label()}</span>
	{/if}
	{notification.title}
{/snippet}
