<script lang="ts">
	import type { Pathname } from '$app/types';
	import type { CurrentUserDto } from '$lib/api/generated';
	import type { Component } from 'svelte';

	import { resolve } from '$app/paths';
	import MenuGroup from '$lib/components/MenuGroup.svelte';
	import { Button } from '$lib/components/ui/button';
	import * as Item from '$lib/components/ui/item';
	import { getPwaService } from '$lib/services/pwa.svelte';
	import { type DevicePushState, getDevicePushState } from '$lib/utils/pushSubscription';
	import { Bell, CalendarHeart, ChevronRight, Download, Ticket, UserPlus } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import { getReadyProgress, type InstallState, type ReadyStepKey } from './readySteps';

	interface Props {
		heading: string;
		/**
		 * Give the top step a filled button. Only when nothing else on the page is
		 * the primary action: emphasis that competes with the live programme or the
		 * voting card stops reading as emphasis (https://lawsofux.com/von-restorff-effect/).
		 */
		emphasizeFirst: boolean;
		user: CurrentUserDto | null;
		hasProgramme: boolean;
		hasSubscriptions: boolean;
		votingEnded: boolean;
		ticketAskedElsewhere: boolean;
	}

	let {
		heading,
		emphasizeFirst,
		user,
		hasProgramme,
		hasSubscriptions,
		votingEnded,
		ticketAskedElsewhere
	}: Props = $props();

	const pwa = getPwaService();

	// Read once per visit: coming back from the notifications page remounts home,
	// which re-checks. 'unknown' until the browser answers keeps the step out
	// rather than flashing a step that turns out to be done.
	let devicePush = $state<DevicePushState>('unknown');

	onMount(() => {
		void getDevicePushState().then((state) => {
			devicePush = state;
		});
	});

	// A messenger channel counts too: reminders reach the user without push.
	let messengerNotificationsOn = $derived.by(() => {
		if (!user) return false;
		const providers = user.social_identities.map((identity) => identity.provider);
		const telegramOn =
			providers.includes('telegram') && user.settings.receive_telegram_notifications;
		const vkOn = providers.includes('vk') && user.settings.receive_vk_notifications;
		return telegramOn || vkOn;
	});

	let notificationsOn = $derived.by(() => {
		if (messengerNotificationsOn || devicePush === 'on') return true;
		if (devicePush === 'off') return false;
		return null;
	});

	let install = $derived.by<InstallState>(() => {
		if (pwa.isInstalled) return 'installed';
		if (pwa.canInstall) return 'available';
		return 'unavailable';
	});

	let progress = $derived(
		getReadyProgress({
			signedIn: user !== null,
			hasTicket: user?.ticket != null,
			votingEnded,
			ticketAskedElsewhere,
			hasProgramme,
			hasSubscriptions,
			notificationsOn,
			install,
			installBeforeNotifications: pwa.isApplePlatform
		})
	);

	// A counter on a one-step list says nothing the step doesn't.
	let showCounter = $derived(progress.total > 1);

	interface ReadyStep {
		title: string;
		description: string;
		icon: Component;
		actionLabel: string;
		href?: Pathname;
		onclick?: () => void;
	}

	let installDescription = $derived(
		pwa.isApplePlatform
			? 'На iPhone уведомления приходят только в установленное приложение.'
			: 'Быстрый доступ с главного экрана и пуш-уведомления.'
	);

	function stepFor(key: ReadyStepKey): ReadyStep {
		switch (key) {
			case 'account':
				return {
					title: 'Создать аккаунт',
					description: 'Нужен для голосования и подписки на выступления программы.',
					icon: UserPlus,
					actionLabel: 'Создать',
					href: '/login'
				};
			case 'ticket':
				return {
					title: 'Привязать билет',
					description: 'Открывает доступ к голосованию в конкурсных номинациях.',
					icon: Ticket,
					actionLabel: 'Привязать',
					href: '/profile/ticket'
				};
			case 'subscribe':
				return {
					title: 'Подписаться на выступления',
					description:
						'Отметь интересные номера в программе — напомним, когда до них дойдёт очередь.',
					icon: CalendarHeart,
					actionLabel: 'К программе',
					href: '/schedule'
				};
			case 'notifications':
				return {
					title: 'Включить уведомления',
					description: 'Напоминания о выступлениях и новости фестиваля придут сразу на телефон.',
					icon: Bell,
					actionLabel: 'Включить',
					href: '/profile/notifications'
				};
			case 'install':
				return {
					title: 'Установить приложение',
					description: installDescription,
					icon: Download,
					actionLabel: 'Установить',
					// Open the install dialog directly; the library handles per-platform UX.
					onclick: () => pwa.showInstallDialog()
				};
		}
	}
</script>

{#snippet stepBody(step: ReadyStep)}
	<Item.Media class="size-9 rounded-lg bg-primary/10 text-primary">
		<step.icon class="size-5" aria-hidden="true" />
	</Item.Media>
	<Item.Content>
		<Item.Title class="text-base">{step.title}</Item.Title>
		<!-- Unclamped: the description is the reason to do the step, so it reads whole. -->
		<Item.Description class="line-clamp-none">{step.description}</Item.Description>
	</Item.Content>
{/snippet}

<!-- The whole row is the target, as in the profile hub. -->
{#snippet plainRow(step: ReadyStep)}
	<!-- hover:bg-muted by hand on the button: Item only highlights rows rendered as <a>. -->
	<Item.Root class="rounded-none hover:bg-muted">
		{#snippet child({ props })}
			{#if step.href}
				<a href={resolve(step.href)} {...props}>
					{@render stepBody(step)}
					<Item.Actions>
						<ChevronRight class="size-4 text-muted-foreground" aria-hidden="true" />
					</Item.Actions>
				</a>
			{:else}
				<button type="button" {...props} onclick={step.onclick}>
					{@render stepBody(step)}
				</button>
			{/if}
		{/snippet}
	</Item.Root>
{/snippet}

<!-- The row stays static and the button is the target: a button inside a
     row-wide link would nest interactive elements. -->
{#snippet emphasizedRow(step: ReadyStep)}
	<Item.Root class="rounded-none">
		{@render stepBody(step)}
		<Item.Actions class="basis-full justify-end sm:basis-auto">
			{#if step.href}
				<Button href={resolve(step.href)} size="sm">{step.actionLabel}</Button>
			{:else}
				<Button size="sm" onclick={step.onclick}>{step.actionLabel}</Button>
			{/if}
		</Item.Actions>
	</Item.Root>
{/snippet}

{#if progress.open.length > 0}
	<section aria-labelledby="get-ready-heading" class="flex flex-col gap-3">
		<div class="flex items-baseline justify-between gap-3">
			<h2 id="get-ready-heading" class="text-lg font-semibold text-foreground">{heading}</h2>
			{#if showCounter}
				<p class="shrink-0 text-sm text-muted-foreground">
					Готово {progress.done} из {progress.total}
				</p>
			{/if}
		</div>

		<MenuGroup>
			{#each progress.open as key, index (key)}
				{@const step = stepFor(key)}
				{#if emphasizeFirst && index === 0}
					{@render emphasizedRow(step)}
				{:else}
					{@render plainRow(step)}
				{/if}
			{/each}
		</MenuGroup>
	</section>
{/if}
