<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { clearOAuthErrorParam, OAUTH_LINK_ERROR_PARAM } from '$lib/utils/oauthErrors';
	import { onMount } from 'svelte';

	import type { PageProps } from './$types';

	import BasicUserInfoCard from '../components/BasicUserInfoCard.svelte';
	import SecurityCard from '../components/SecurityCard.svelte';

	let { data }: PageProps = $props();
	let user = $derived(data.user!);
	let enabledProviders = $derived(data.enabledProviders);
	const toastService = getToastService();

	// Cancelling is the user's own choice, so it gets an informational toast —
	// only a flow that actually broke reads as an error.
	const linkErrorToasts = {
		cancelled: { message: 'Подключение отменено.', type: 'info' },
		failed: { message: 'Не удалось подключить аккаунт. Попробуй ещё раз.', type: 'error' },
		linked_to_another_account: {
			message: 'Этот аккаунт уже подключён к другому профилю.',
			type: 'error'
		},
		user_already_has_provider: {
			message: 'К твоему аккаунту уже подключён аккаунт этого сервиса.',
			type: 'error'
		},
		session_changed: {
			message: 'Вход в аккаунт сменился, пока шло подключение. Попробуй ещё раз.',
			type: 'error'
		}
	} as const;

	// Refreshing the current user also refreshes connections — they ship together now.
	async function refreshProfile() {
		await invalidate('app:current-user');
	}

	onMount(() => {
		const linkError = data.oauthLinkError;

		if (!linkError) return;

		const toast = linkErrorToasts[linkError];
		toastService.add(toast.message, toast.type);

		// Keep the page in place and remove the one-time error flag from the address bar.
		clearOAuthErrorParam(OAUTH_LINK_ERROR_PARAM);
	});
</script>

<svelte:head>
	<title>Аккаунт · ФАН ФАН</title>
</svelte:head>

<BasicUserInfoCard {user} onUpdate={refreshProfile} />
<SecurityCard {user} {enabledProviders} onUpdate={refreshProfile} />
