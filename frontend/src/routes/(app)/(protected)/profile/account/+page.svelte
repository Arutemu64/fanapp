<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import { listOauthProvidersOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { currentUserOptions } from '#lib/api/index.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { clearOAuthErrorParam, OAUTH_LINK_ERROR_PARAM } from '#lib/utils/oauthErrors.js';

	import type { PageProps } from './$types';

	import ProfileHeader from '../components/ProfileHeader.svelte';
	import SignInMethods from '../components/SignInMethods.svelte';

	let { data }: PageProps = $props();
	const userQuery = createQuery(() => currentUserOptions());
	// Live from the query; the guard's snapshot covers the moment a session expiry
	// has emptied it but not yet moved us to /login.
	let user = $derived(userQuery.data ?? data.user);

	// Which providers can be *linked* is the same deployment gate the login screen
	// reads — a provider unreachable from this host offers no "connect" button. Read
	// at runtime, not baked in. An already-linked provider stays unlinkable even when
	// disabled (that row comes from the user, and the unlink route is never gated), so
	// a failure here just drops the connect affordances, never the ability to unlink.
	const providersQuery = createQuery(() => listOauthProvidersOptions());
	let enabledProviders = $derived(providersQuery.data?.providers ?? []);
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

<ProfileHeader {user} />
<SignInMethods {user} {enabledProviders} />
