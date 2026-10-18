<script lang="ts">
	import type { Attachment } from 'svelte/attachments';

	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Mail from '@lucide/svelte/icons/mail';
	import { onMount } from 'svelte';

	import { Button } from '#lib/components/ui/button/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { clearOAuthErrorParam, OAUTH_LOGIN_ERROR_PARAM } from '#lib/utils/oauthErrors.js';

	import type { PageProps } from './$types';

	import CodeLoginForm from './components/CodeLoginForm.svelte';
	import PasswordLoginForm from './components/PasswordLoginForm.svelte';
	import SocialLoginButtons from './components/SocialLoginButtons.svelte';
	import VerifyCodeForm from './components/VerifyCodeForm.svelte';

	let { data }: PageProps = $props();
	const toastService = getToastService();

	// The first screen offers the login options only; the email form (and the
	// captcha proof-of-work it starts on mount) lives on its own step, so someone
	// using an OAuth provider never runs it. 'password' is a factor under 'email', not a
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
		cancelled: { message: m.login_cancelled(), type: 'info' },
		failed: { message: m.login_failed(), type: 'error' }
	} as const;

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

<svelte:head>
	<title>{m.document_title({ title: m.login_title() })}</title>
</svelte:head>

<Card.Root class="w-full p-4 sm:p-6">
	<div class="flex flex-col gap-4">
		{#if step !== 'options'}
			<Button
				variant="ghost"
				class="-my-2 -ml-2.5 self-start text-muted-foreground"
				onclick={goBack}
			>
				<ArrowLeft data-icon="inline-start" />
				{m.common_back()}
			</Button>
		{/if}

		<div class="flex flex-col gap-1 text-center">
			<!-- Just «Вход»: the logo above already names ФАН ФАН. -->
			<h1 class="text-headline text-foreground">{m.login_title()}</h1>
			{#if step === 'options'}
				<!-- Benefits belong on the entry screen only: once a method is chosen the
					sub-steps are the task, not the pitch. Every method — email or social —
					creates the account on first sign-in and there is no separate sign-up,
					so the entry screen says so once rather than leave a newcomer hunting
					for «Регистрация». -->
				<p class="text-sm text-muted-foreground">
					{m.login_intro()}
				</p>
				<p class="text-sm text-muted-foreground">
					{m.login_signup_note()}
				</p>
			{/if}
		</div>

		{#key step}
			<div class="flex flex-col gap-4" {@attach focusStep}>
				{#if step === 'options'}
					<SocialLoginButtons />

					<Button
						type="button"
						variant="outline"
						class="w-full"
						data-step-focus
						onclick={showEmailLogin}
					>
						<Mail data-icon="inline-start" />
						{m.login_via_email()}
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
			{m.login_continue_guest()}
		</button>
	</div>
{/if}
