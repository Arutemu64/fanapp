<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { PUBLIC_APP_VERSION } from '$env/static/public';
	import StaleDataNotice from '$lib/components/StaleDataNotice.svelte';
	import { getOfflineService } from '$lib/services/offline.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { HeartOutline } from 'flowbite-svelte-icons';
	import { onMount } from 'svelte';
	import IconFastapi from '~icons/simple-icons/fastapi';
	import IconSvelte from '~icons/simple-icons/svelte';

	import type { PageProps } from './$types';

	import BasicUserInfoCard from './components/BasicUserInfoCard.svelte';
	import PushNotificationsCard from './components/PushNotificationsCard.svelte';
	import PwaInstallCard from './components/PwaInstallCard.svelte';
	import SecurityCard from './components/SecurityCard.svelte';
	import TicketLinkCard from './components/TicketLinkCard.svelte';

	let { data }: PageProps = $props();
	let user = $derived(data.user!);
	const toastService = getToastService();

	// The whole profile (identity + connections) renders from the layout-cached
	// user, so the only "out of date" state left is being offline.
	const offline = getOfflineService();
	let showStaleNotice = $derived(!offline.isOnline);
	const staleNoticeMessage = 'Нет связи. Показан сохранённый профиль — обновится при подключении.';

	// Commit SHA baked in at build time, shortened for display. Empty for a local
	// build from source — then the line is hidden rather than showing a blank id.
	// It exists so a bug report ("у меня всё сломалось") names an exact bundle.
	const buildId = PUBLIC_APP_VERSION.slice(0, 7);

	const telegramLinkErrorMessages = {
		linked_to_another_account: 'Этот Telegram уже подключён к другому аккаунту.',
		user_already_has_telegram: 'К вашему аккаунту уже подключён другой Telegram.'
	} as const;

	// Refreshing the current user also refreshes connections — they ship together now.
	async function refreshProfile() {
		await invalidate('app:current-user');
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

<div class="flex flex-col gap-4 sm:gap-5">
	{#if showStaleNotice}
		<StaleDataNotice message={staleNoticeMessage} />
	{/if}

	<!-- Identity banner anchors the page; the settings group sits below it. -->
	<BasicUserInfoCard {user} onUpdate={refreshProfile} />

	<div class="grid items-start gap-4 sm:grid-cols-2 sm:gap-5">
		<div class="flex flex-col gap-4">
			<TicketLinkCard {user} onTicketLinked={refreshProfile} />
			<SecurityCard {user} onUpdate={refreshProfile} />
		</div>

		<div class="flex flex-col gap-4">
			<PwaInstallCard />

			<PushNotificationsCard {user} onSettingsUpdate={refreshProfile} />
		</div>
	</div>
</div>

<footer class="mt-6 pb-4 text-center text-xs text-gray-500 dark:text-gray-400">
	<p class="flex items-center justify-center gap-1">
		Работает на
		<IconSvelte class="inline size-3.5 text-[#FF3E00]" />
		Svelte и
		<IconFastapi class="inline size-3.5 text-[#009688]" />
		FastAPI
	</p>
	<p class="mt-0.5 flex items-center justify-center gap-1">
		С любовью, Arutemu64
		<HeartOutline class="inline size-3.5 text-red-400" />
	</p>
	{#if buildId}
		<p class="mt-0.5">Сборка {buildId}</p>
	{/if}
</footer>
