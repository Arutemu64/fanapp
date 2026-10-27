<script lang="ts">
	import { PUBLIC_API_URL } from '$app/env/public';
	import { page } from '$app/state';
	import { createQuery } from '@tanstack/svelte-query';
	import { onDestroy } from 'svelte';

	import type { SocialProvider } from '#lib/api/generated/index.js';

	import { listOauthProvidersOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { ALL_SOCIAL_PROVIDERS, SOCIAL_PROVIDER_PRESENTATION } from '#lib/data/socialProviders.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getSession } from '#lib/services/session.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { LOGIN_NEXT_PARAM, sanitizeNextPath } from '#lib/utils/auth.js';

	const toastService = getToastService();
	const session = getSession();

	const providersQuery = createQuery(() => listOauthProvidersOptions());
	const providers = $derived(providersQuery.data?.providers ?? ALL_SOCIAL_PROVIDERS);

	let openingProvider = $state<SocialProvider | null>(null);
	let abandoned = false;
	onDestroy(() => {
		abandoned = true;
	});

	let nextPath = $derived(sanitizeNextPath(page.url.searchParams.get(LOGIN_NEXT_PARAM)));

	function providerStartUrl(provider: SocialProvider): string {
		const url = `${PUBLIC_API_URL}/auth/oauth/${provider}/start`;
		if (!nextPath) return url;

		const query = new URLSearchParams({ [LOGIN_NEXT_PARAM]: nextPath });
		return `${url}?${query}`;
	}

	async function handleProviderClick(event: MouseEvent, provider: SocialProvider) {
		if (openingProvider !== null) {
			event.preventDefault();
			return;
		}

		openingProvider = provider;
		if (!session.logoutPending) return;

		event.preventDefault();
		const settled = await session.settlePendingLogout();
		if (abandoned) return;
		if (settled) {
			window.location.assign(providerStartUrl(provider));
			return;
		}
		openingProvider = null;
		toastService.add(m.login_previous_logout_failed(), 'error');
	}
</script>

<svelte:window
	onpageshow={() => {
		openingProvider = null;
	}}
/>

{#each providers as provider (provider)}
	{const meta = $derived(SOCIAL_PROVIDER_PRESENTATION[provider])}
	{const Icon = $derived(meta.icon)}
	<Button
		href={providerStartUrl(provider)}
		variant="outline"
		class="w-full"
		aria-disabled={openingProvider === provider}
		onclick={(event: MouseEvent) => void handleProviderClick(event, provider)}
	>
		{#if openingProvider === provider}
			<Spinner data-icon="inline-start" />
			{m.login_opening_provider({ name: meta.name })}
		{:else}
			<Icon class={meta.iconClass} data-icon="inline-start" />
			{m.login_via_provider({ name: meta.name })}
		{/if}
	</Button>
{/each}
