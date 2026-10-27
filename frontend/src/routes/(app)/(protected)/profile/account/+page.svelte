<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import { listOauthProvidersOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { m } from '#lib/paraglide/messages.js';
	import { currentUserOptions } from '#lib/services/identity.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { clearOAuthErrorParam, OAUTH_LINK_ERROR_PARAM } from '#lib/utils/oauthErrors.js';

	import type { PageProps } from './$types';

	import ProfileHeader from '../components/ProfileHeader.svelte';
	import SignInMethods from '../components/SignInMethods.svelte';

	let { data }: PageProps = $props();
	const userQuery = createQuery(() => currentUserOptions());
	let user = $derived(userQuery.data ?? data.user);

	const providersQuery = createQuery(() => listOauthProvidersOptions());
	let enabledProviders = $derived(providersQuery.data?.providers ?? []);
	const toastService = getToastService();

	const linkErrorToasts = {
		cancelled: { message: m.account_link_cancelled(), type: 'info' },
		failed: { message: m.account_link_failed(), type: 'error' },
		linked_to_another_account: {
			message: m.account_link_conflict(),
			type: 'error'
		},
		user_already_has_provider: {
			message: m.account_link_provider_taken(),
			type: 'error'
		},
		session_changed: {
			message: m.account_link_initiator_mismatch(),
			type: 'error'
		}
	} as const;

	onMount(() => {
		const linkError = data.oauthLinkError;

		if (!linkError) return;

		const toast = linkErrorToasts[linkError];
		toastService.add(toast.message, toast.type);

		clearOAuthErrorParam(OAUTH_LINK_ERROR_PARAM);
	});
</script>

<svelte:head>
	<title>{m.document_title({ title: m.account_title() })}</title>
</svelte:head>

<ProfileHeader {user} />
<SignInMethods {user} {enabledProviders} />
