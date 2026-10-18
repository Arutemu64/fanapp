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

	// Which social login buttons to show is a per-deployment backend decision — a
	// provider can be built in yet unreachable from this host (Telegram is blocked
	// on Russian hosting) — so it is read at runtime, not baked into the bundle.
	//
	// No answer yet (first visit, offline, an error) is NOT the same as "none
	// enabled": it must not hide every social button, or a social-only account (no
	// password, and its OAuth email was never stored) loses its only way in. So the
	// page fails open to every known provider; a disabled one is still rejected by
	// its start endpoint, so the worst case is a handled error, never a lockout. An
	// authoritative empty list stays empty.
	const providersQuery = createQuery(() => listOauthProvidersOptions());
	const providers = $derived(providersQuery.data?.providers ?? ALL_SOCIAL_PROVIDERS);

	// Starting an OAuth login is a full-page navigation that waits on our backend
	// and on the provider's discovery/authorize page, so the button has to say it
	// was heard. Tracking which provider is opening lets each button show its own
	// spinner while a pending navigation blocks starting a second one.
	let openingProvider = $state<SocialProvider | null>(null);
	// Set once these buttons go away (the user picked email, or left the page with
	// "continue without login") while a provider click still waits on a
	// pending-logout revoke, so the late callback doesn't drag them off to the
	// provider after all.
	let abandoned = false;
	onDestroy(() => {
		abandoned = true;
	});

	// The email forms read `next` straight off the URL in Session.loggedIn; a social
	// login leaves for the provider, so the backend carries it through the OAuth
	// state instead (and re-validates it there) and lands the user on it.
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
		// A logout made offline must be revoked before a new session exists, or the
		// queued revoke would end the new one on return (see settlePendingLogout).
		// Usually the reconnect/boot flush already did it and the link just navigates.
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

<!-- Coming back from a provider restores this page from the bfcache with its DOM
	frozen mid-navigation, so the spinner would still be running. `pageshow` fires
	on that restore (and on a normal load, where the flag is already null). -->
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
