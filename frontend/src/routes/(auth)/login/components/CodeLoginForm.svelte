<script lang="ts">
	import Mail from '@lucide/svelte/icons/mail';
	import { createMutation } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import { requestLoginCodeMutation } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import FormError from '#lib/components/FormError.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import * as InputGroup from '#lib/components/ui/input-group/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { Captcha } from '#lib/services/captcha.svelte.js';
	import { isValidEmail, normalizeEmail } from '#lib/utils/validation.js';

	interface Props {
		email: string;
		onCodeSent: (sentTo: string) => void;
		onPasswordLogin?: () => void;
	}

	let { email = $bindable(''), onCodeSent, onPasswordLogin }: Props = $props();

	const requestCodeMutation = createMutation(() => requestLoginCodeMutation());
	let emailError = $state('');
	let formError = $state('');

	const captcha = new Captcha();

	let isRequesting = $derived(requestCodeMutation.isPending || captcha.solving);

	onMount(() => {
		captcha.prefetch();
		return () => captcha.dispose();
	});

	let normalizedEmail = $derived(normalizeEmail(email));

	function resetEmailFeedback() {
		emailError = '';
		formError = '';
	}

	function validateEmailCodeRequestForm(): boolean {
		emailError = '';

		if (!normalizedEmail) {
			emailError = m.validation_email_required();
			return false;
		}

		if (!isValidEmail(normalizedEmail)) {
			emailError = m.validation_email_format();
			return false;
		}

		return true;
	}

	async function handleLoginCodeRequest() {
		if (isRequesting) {
			return;
		}

		if (!validateEmailCodeRequestForm()) {
			return;
		}

		const trimmedEmail = normalizedEmail;
		let captchaToken: string | null;
		try {
			captchaToken = await captcha.take();
		} catch (error) {
			formError = getApiErrorDetail(error) ?? m.captcha_failed();
			captcha.prefetch();
			return;
		}

		requestCodeMutation.mutate(
			{ body: { email: trimmedEmail, captcha_token: captchaToken } },
			{
				onSuccess: () => onCodeSent(trimmedEmail),
				onError: (error) => {
					const emailFieldError = getApiFieldError(error, 'email');
					if (emailFieldError) {
						emailError = emailFieldError;
					} else {
						formError = getApiErrorDetail(error) ?? m.login_code_send_failed();
					}
					captcha.prefetch();
				}
			}
		);
	}

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		void handleLoginCodeRequest();
	}
</script>

<form novalidate onsubmit={handleSubmit} class="flex flex-col gap-4">
	<FormError message={formError} />

	<Field.Field data-invalid={emailError ? true : undefined}>
		<Field.FieldLabel for="code-email">{m.email_label()}</Field.FieldLabel>
		<InputGroup.Root>
			<InputGroup.Addon>
				<Mail aria-hidden="true" />
			</InputGroup.Addon>
			<InputGroup.Input
				id="code-email"
				name="email"
				type="email"
				bind:value={email}
				placeholder="name@example.com"
				autocomplete="username"
				inputmode="email"
				autocapitalize="off"
				spellcheck={false}
				required
				readonly={isRequesting}
				aria-invalid={emailError ? true : undefined}
				aria-describedby={emailError ? 'code-email-error' : 'code-email-description'}
				oninput={resetEmailFeedback}
			/>
		</InputGroup.Root>
		{#if emailError}
			<Field.FieldError id="code-email-error">{emailError}</Field.FieldError>
		{:else}
			<Field.FieldDescription id="code-email-description">
				{m.login_code_hint()}
			</Field.FieldDescription>
		{/if}
	</Field.Field>

	<Button type="submit" class="w-full" disabled={isRequesting}>
		{#if isRequesting}
			<Spinner data-icon="inline-start" />
			{m.common_sending()}
		{:else}
			{m.common_continue()}
		{/if}
	</Button>

	<div class="text-center">
		<button
			type="button"
			class="inline-flex min-h-11 items-center justify-center rounded-lg px-3 text-sm font-medium text-primary hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:opacity-50"
			onclick={() => onPasswordLogin?.()}
			disabled={isRequesting}
		>
			{m.login_with_password()}
		</button>
	</div>
</form>
