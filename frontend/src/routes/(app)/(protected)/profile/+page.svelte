<script lang="ts">
	import { onMount } from 'svelte';
	import BasicUserInfoCard from './components/BasicUserInfoCard.svelte';
	import TicketLinkCard from './components/TicketLinkCard.svelte';
	import PushNotificationsCard from './components/PushNotificationsCard.svelte';
	import SecurityCard from './components/SecurityCard.svelte';
	import PwaInstallCard from './components/PwaInstallCard.svelte';
	import IconSvelte from '~icons/simple-icons/svelte';
	import IconFastapi from '~icons/simple-icons/fastapi';
	import IconHeart from '~icons/lucide/heart';
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { PageProps } from './$types';
	import { invalidate } from '$app/navigation';

	let { data }: PageProps = $props();
	let user = $derived(data.user!);
	const toastService = getToastService();

	const telegramLinkErrorMessages = {
		linked_to_another_account: 'Этот Telegram уже подключён к другому аккаунту.',
		user_already_has_telegram: 'К вашему аккаунту уже подключён другой Telegram.'
	} as const;

	async function refreshProfile() {
		await Promise.all([
			invalidate('app:current-user'),
			invalidate('app:push-subscriptions'),
			invalidate('app:social-accounts')
		]);
	}

	onMount(() => {
		const telegramLinkError = data.telegramLinkError;

		if (!telegramLinkError) return;

		toastService.add(telegramLinkErrorMessages[telegramLinkError], 'error');

		const nextUrl = new URL(window.location.href);
		nextUrl.searchParams.delete('telegramLinkError');

		// Keep the page in place and remove the one-time error flag from the address bar.
		window.history.replaceState(window.history.state, '', nextUrl);
	});
</script>

<svelte:head>
	<title>Профиль · ФАН ФАН</title>
</svelte:head>

<div class="flex flex-col gap-4">
	<!-- Basic User Info Card -->
	<BasicUserInfoCard {user} onUpdate={refreshProfile} />

	<div class="grid items-start gap-4 sm:grid-cols-2">
		<div class="flex flex-col gap-4">
			<!-- Ticket Link Card -->
			<TicketLinkCard {user} onTicketLinked={refreshProfile} />
			<!-- Login Methods Card -->
			<SecurityCard {user} socialAccounts={data.socialAccounts} onUpdate={refreshProfile} />
		</div>

		<div class="flex flex-col gap-4">
			<!-- PWA Install Card -->
			<PwaInstallCard />

			<!-- Push Notifications Card -->
			<PushNotificationsCard
				{user}
				socialAccounts={data.socialAccounts}
				pushSubscriptions={data.pushSubscriptions}
				onSettingsUpdate={refreshProfile}
			/>
		</div>
	</div>
</div>

<footer class="mt-6 pb-4 text-center text-xs text-gray-400 dark:text-gray-500">
	<p class="flex items-center justify-center gap-1">
		Работает на
		<IconSvelte class="inline size-3.5 text-[#FF3E00]" />
		Svelte и
		<IconFastapi class="inline size-3.5 text-[#009688]" />
		FastAPI
	</p>
	<p class="mt-0.5 flex items-center justify-center gap-1">
		С любовью, Arutemu64
		<IconHeart class="inline size-3.5 text-red-400" />
	</p>
</footer>
