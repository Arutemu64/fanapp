<script lang="ts">
	import type { Attachment } from 'svelte/attachments';

	import { PUBLIC_API_URL } from '$app/env/public';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { ArrowLeft, Mail } from '@lucide/svelte';
	import { onMount } from 'svelte';

	import type { SocialProvider } from '#lib/api/generated/index.js';

	import { Button } from '#lib/components/ui/button/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { ALL_SOCIAL_PROVIDERS, SOCIAL_PROVIDER_PRESENTATION } from '#lib/data/socialProviders.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { LOGIN_NEXT_PARAM, sanitizeNextPath } from '#lib/utils/auth.js';
	import { clearOAuthErrorParam, OAUTH_LOGIN_ERROR_PARAM } from '#lib/utils/oauthErrors.js';

	import type { PageProps } from './$types';

	import CodeLoginForm from './components/CodeLoginForm.svelte';
	import PasswordLoginForm from './components/PasswordLoginForm.svelte';
	import VerifyCodeForm from './components/VerifyCodeForm.svelte';

	let { data }: PageProps = $props();
	const toastService = getToastService();

	// `null` means the providers probe couldn't be reached (see +page.ts); fail open
	// to every known provider so a social-only account is never hidden by a hiccup.
	const providers = $derived(data.enabledProviders ?? ALL_SOCIAL_PROVIDERS);

	// The first screen offers the login options only; the email form (and its
	// third-party captcha script) lives on its own step, so someone using an
	// OAuth provider never loads it. 'password' is a factor under 'email', not a
	// peer option, so it's reached from the email step rather than the options.
	//
	// Each step is its own history entry (shallow routing), so the phone's back
	// gesture steps back through the flow instead of leaving the login page —
	// https://svelte.dev/docs/kit/shallow-routing. page.state is empty after a
	// reload, which lands on the options screen.
	const step = $derived(page.state.loginStep ?? 'options');
	const codeSentTo = $derived(page.state.loginCodeEmail);

	// Kept on the parent so it survives every step switch.
	let email = $state('');

	// Cancelling is the user's own choice, so it gets an informational toast —
	// only a flow that actually broke reads as an error.
	const loginErrorToasts = {
		cancelled: { message: 'Вход отменён.', type: 'info' },
		failed: { message: 'Не удалось войти. Попробуй ещё раз.', type: 'error' }
	} as const;

	// Starting an OAuth login is a full-page navigation that waits on our backend
	// and on the provider's discovery/authorize page, so the button has to say it
	// was heard. Tracking which provider is opening lets each button show its own
	// spinner while a pending navigation blocks starting a second one.
	let openingProvider = $state<SocialProvider | null>(null);

	// The email forms read `next` straight off the URL in completeLogin; a social
	// login leaves for the provider, so the backend carries it through the OAuth
	// state instead (and re-validates it there) and lands the user on it.
	let nextPath = $derived(sanitizeNextPath(page.url.searchParams.get(LOGIN_NEXT_PARAM)));

	function providerStartUrl(provider: SocialProvider): string {
		const url = `${PUBLIC_API_URL}/auth/oauth/${provider}/start`;
		if (!nextPath) return url;

		const query = new URLSearchParams({ [LOGIN_NEXT_PARAM]: nextPath });
		return `${url}?${query}`;
	}

	function handleProviderClick(event: MouseEvent, provider: SocialProvider) {
		if (openingProvider !== null) {
			event.preventDefault();
			return;
		}

		// Don't cancel a pending offline-logout here — clearing it before OAuth
		// *succeeds* would let a cancelled/abandoned login drop the revoke, leaving the
		// valid HttpOnly cookie to restore the old account. The reconnect/boot flush
		// clears the intent once the old session is actually revoked, which in practice
		// runs before the user reaches this button, so a genuine new login still starts
		// from a cleared intent. (A client-only "did OAuth succeed?" signal can't tell
		// success from an abandoned flow, so we don't try — see the PR discussion.)
		openingProvider = provider;
	}

	function showEmailLogin() {
		void goto('', { shallow: true, state: { loginStep: 'email' } });
	}

	function showPasswordLogin() {
		void goto('', { shallow: true, state: { loginStep: 'password' } });
	}

	function showCodeStep(sentTo: string) {
		void goto('', {
			shallow: true,
			state: { loginStep: 'code', loginCodeEmail: sentTo }
		});
	}

	// The on-screen back control walks the same history as the back gesture, so
	// the two can never disagree about where "back" is.
	function goBack() {
		history.back();
	}

	// A step swap removes the control that opened it, dropping focus to <body>, so
	// move focus into the new step: its first empty field, else its first field,
	// else its marked default control. Skipped on the first render — that is always
	// the options screen, where focus belongs at the top of the page.
	let isFirstRender = true;
	const focusStep: Attachment<HTMLElement> = (node) => {
		if (isFirstRender) {
			isFirstRender = false;
			return;
		}

		const fields = Array.from(
			node.querySelectorAll<HTMLInputElement>('input:not([type="hidden"])')
		);
		const target =
			fields.find((field) => !field.value) ??
			fields.at(0) ??
			node.querySelector<HTMLElement>('[data-step-focus]');
		target?.focus();
	};

	onMount(() => {
		const loginError = data.oauthLoginError;

		if (!loginError) return;

		const toast = loginErrorToasts[loginError];
		toastService.add(toast.message, toast.type);

		clearOAuthErrorParam(OAUTH_LOGIN_ERROR_PARAM);
	});
</script>

<!-- Coming back from a provider restores this page from the bfcache with its DOM
	frozen mid-navigation, so the spinner would still be running. `pageshow` fires
	on that restore (and on a normal load, where the flag is already null). -->
<svelte:window
	onpageshow={() => {
		openingProvider = null;
	}}
/>

<svelte:head>
	<title>Вход · ФАН ФАН</title>
</svelte:head>

<Card.Root class="w-full rounded-2xl p-4 sm:p-6">
	<div class="flex flex-col gap-4">
		{#if step !== 'options'}
			<Button
				variant="ghost"
				class="-my-2 -ml-2.5 self-start text-muted-foreground"
				onclick={goBack}
			>
				<ArrowLeft data-icon="inline-start" />
				Назад
			</Button>
		{/if}

		<div class="flex flex-col gap-1 text-center">
			<!-- Just «Вход»: the logo above already names ФАН ФАН. -->
			<h1 class="text-2xl font-bold text-foreground">Вход</h1>
			{#if step === 'options'}
				<!-- Benefits belong on the entry screen only: once a method is chosen the
					sub-steps are the task, not the pitch. Every method — email or social —
					creates the account on first sign-in and there is no separate sign-up,
					so the entry screen says so once rather than leave a newcomer hunting
					for «Регистрация». -->
				<p class="text-sm text-muted-foreground">
					Получай персональные уведомления, голосуй за участников и оставляй обратную связь.
				</p>
				<p class="text-sm text-muted-foreground">
					Аккаунта ещё нет? Он создастся при первом входе.
				</p>
			{/if}
		</div>

		{#key step}
			<div class="flex flex-col gap-4" {@attach focusStep}>
				{#if step === 'options'}
					{#each providers as provider (provider)}
						{@const meta = SOCIAL_PROVIDER_PRESENTATION[provider]}
						{@const Icon = meta.icon}
						<Button
							href={providerStartUrl(provider)}
							variant="outline"
							class="w-full"
							aria-disabled={openingProvider === provider}
							onclick={(event: MouseEvent) => handleProviderClick(event, provider)}
						>
							{#if openingProvider === provider}
								<Spinner data-icon="inline-start" />
								Открываем {meta.name}…
							{:else}
								<Icon class={meta.iconClass} data-icon="inline-start" />
								Войти через {meta.name}
							{/if}
						</Button>
					{/each}

					<Button
						type="button"
						variant="outline"
						class="w-full"
						data-step-focus
						onclick={showEmailLogin}
					>
						<Mail data-icon="inline-start" />
						Войти по почте
					</Button>
				{:else if step === 'code' && codeSentTo}
					<VerifyCodeForm email={codeSentTo} />
				{:else if step === 'password'}
					<PasswordLoginForm bind:email onCodeLogin={goBack} />
				{:else}
					<CodeLoginForm bind:email onCodeSent={showCodeStep} onPasswordLogin={showPasswordLogin} />
				{/if}
			</div>
		{/key}
	</div>
</Card.Root>

<!--
	The app is usable by guests, and login is reached both voluntarily (navbar)
	and via protected-route redirects, so always offer a way back into it.
	Navigate to the app root explicitly instead of history.back(): going back
	would re-enter a protected redirect straight to /login, and a direct
	deep-link to /login has no history to return to.

	Options screen only: a sub-step already has «Назад» at the top, and one exit
	per screen keeps the stack short; leaving from there is one tap further.
-->
{#if step === 'options'}
	<div class="text-center">
		<button
			type="button"
			class="inline-flex min-h-11 items-center justify-center rounded-lg px-3 text-sm font-medium text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
			onclick={() => goto(resolve(''))}
		>
			Продолжить без входа
		</button>
	</div>
{/if}
