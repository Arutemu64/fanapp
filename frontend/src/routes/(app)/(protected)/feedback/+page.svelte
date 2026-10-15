<script lang="ts">
	import { createMutation } from '@tanstack/svelte-query';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import { submitFeedbackMutation } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import OfflineUnavailableState from '#lib/components/OfflineUnavailableState.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { Textarea } from '#lib/components/ui/textarea/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const toastService = getToastService();

	const MAX_LENGTH = 2000;

	let feedbackText = $state('');
	const feedbackMutation = createMutation(() => submitFeedbackMutation());
	const offlineGate = offlineWriteGate();

	let feedbackError = $state('');
	let submitError = $state('');

	let charsLeft = $derived(MAX_LENGTH - feedbackText.length);
	// Opened offline and still offline: clears on reconnect without a reload, and
	// a connection that drops mid-draft keeps the form (its submit is gated and
	// explains itself) rather than unmounting what was typed.
	let showOffline = $derived(data.offlineUnavailable && !reachability.current);

	function validateForm() {
		if (!feedbackText.trim()) {
			feedbackError = m.feedback_validation_empty();
			return false;
		}
		feedbackError = '';
		return true;
	}

	function handleInput() {
		if (feedbackError) {
			feedbackError = feedbackText.trim() ? '' : m.feedback_validation_empty();
		}
	}

	function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';

		if (!validateForm()) {
			return;
		}

		feedbackMutation.mutate(
			{ body: { text: feedbackText.trim() } },
			{
				onSuccess: () => {
					toastService.add(m.feedback_sent(), 'success');
					feedbackText = '';
					feedbackError = '';
				},
				onError: (error) => {
					const textError = getApiFieldError(error, 'text');
					if (textError) {
						feedbackError = textError;
						return;
					}
					submitError = getApiErrorDetail(error) ?? m.feedback_send_failed();
				}
			}
		);
	}
</script>

<svelte:head>
	<title>{m.document_title({ title: m.feedback_title() })}</title>
</svelte:head>

{#if showOffline}
	<!-- Submit-only surface with nothing to cache: say so plainly rather than
	     showing a form that can't send. -->
	<OfflineUnavailableState
		title={m.feedback_offline_title()}
		message={m.feedback_offline_message()}
	/>
{:else}
	<div class="mx-auto w-full max-w-2xl">
		<SectionIntro description={m.feedback_description()} />

		<form class="flex flex-col gap-6" onsubmit={offlineGate.guard(handleSubmit)}>
			<Field.Field data-invalid={feedbackError ? true : undefined}>
				<Field.FieldLabel for="feedback-text">{m.feedback_field_label()}</Field.FieldLabel>
				<Textarea
					id="feedback-text"
					name="text"
					rows={6}
					maxlength={MAX_LENGTH}
					placeholder={m.feedback_placeholder()}
					bind:value={feedbackText}
					disabled={feedbackMutation.isPending}
					oninput={handleInput}
					aria-invalid={feedbackError ? true : undefined}
					class="resize-none"
				/>
				{#if feedbackError}
					<Field.FieldError>{feedbackError}</Field.FieldError>
				{:else}
					<Field.FieldDescription>
						{m.feedback_chars_left({ count: charsLeft })}
					</Field.FieldDescription>
				{/if}
			</Field.Field>

			{#if submitError}
				<Alert.Root variant="destructive">
					<Alert.Description>{submitError}</Alert.Description>
				</Alert.Root>
			{/if}

			<Button
				type="submit"
				class="w-full sm:w-auto"
				disabled={feedbackMutation.isPending}
				aria-disabled={offlineGate.blocked}
			>
				{#if feedbackMutation.isPending}
					<Spinner data-icon="inline-start" />
					{m.common_sending()}
				{:else}
					{m.feedback_submit()}
				{/if}
			</Button>
		</form>
	</div>
{/if}
