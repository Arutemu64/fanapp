<script lang="ts">
	import type { Pathname } from '$app/types';
	import type { CurrentUserDto } from '$lib/api/generated';
	import type { Component } from 'svelte';

	import { getPwaService } from '$lib/services/pwa.svelte';
	import { type DevicePushState, getDevicePushState } from '$lib/utils/pushSubscription';
	import { Bell, CalendarHeart, Download, Ticket, UserPlus } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import GetReadyCard from './GetReadyCard.svelte';
	import { getReadySteps, type ReadyStepKey } from './readySteps';

	interface Props {
		heading: string;
		user: CurrentUserDto | null;
		hasProgramme: boolean;
		hasSubscriptions: boolean;
		votingEnded: boolean;
		ticketAskedElsewhere: boolean;
	}

	let { heading, user, hasProgramme, hasSubscriptions, votingEnded, ticketAskedElsewhere }: Props =
		$props();

	const pwa = getPwaService();

	// Read once per visit: coming back from the notifications page remounts home,
	// which re-checks. 'unknown' until the browser answers keeps the step hidden
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

	let steps = $derived(
		getReadySteps({
			signedIn: user !== null,
			hasTicket: user?.ticket != null,
			votingEnded,
			ticketAskedElsewhere,
			hasProgramme,
			hasSubscriptions,
			notificationsOn,
			canInstall: pwa.canInstall,
			installBeforeNotifications: pwa.isApplePlatform
		})
	);

	interface ReadyCard {
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

	function cardFor(key: ReadyStepKey): ReadyCard {
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

	// Lead with the top step as a prominent card; the rest fill a compact grid.
	let featuredKey = $derived(steps.at(0));
	let restKeys = $derived(steps.slice(1));
</script>

{#snippet card(key: ReadyStepKey, featured: boolean)}
	{@const step = cardFor(key)}
	<GetReadyCard
		{featured}
		title={step.title}
		description={step.description}
		icon={step.icon}
		actionLabel={step.actionLabel}
		href={step.href}
		onclick={step.onclick}
	/>
{/snippet}

{#if featuredKey}
	<section aria-labelledby="get-ready-heading" class="flex flex-col gap-3">
		<h2 id="get-ready-heading" class="text-lg font-semibold text-foreground">{heading}</h2>

		<div class="flex flex-col gap-3">
			{@render card(featuredKey, true)}

			{#if restKeys.length > 0}
				<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
					{#each restKeys as key (key)}
						{@render card(key, false)}
					{/each}
				</div>
			{/if}
		</div>
	</section>
{/if}
