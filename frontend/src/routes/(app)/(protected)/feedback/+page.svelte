<script lang="ts">
	import { createMutation } from '@tanstack/svelte-query';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import { handOffWhenQueued } from '#lib/api/queuedWrite.svelte.js';
	import { queuedFeedbackOptions } from '#lib/api/writeQueue.js';
	import FormError from '#lib/components/FormError.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { Textarea } from '#lib/components/ui/textarea/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';

	const toastService = getToastService();

	const MAX_LENGTH = 2000;

	let feedbackText = $state('');

	let feedbackError = $state('');
	let submitError = $state('');

	// Queued (ADR-0038): written offline, a message waits for the connection
	// instead of being lost with the draft.
	const feedbackMutation = createMutation(() => queuedFeedbackOptions());
	handOffWhenQueued(feedbackMutation, () => {
		toastService.add(m.feedback_queued(), 'info');
		feedbackText = '';
		feedbackError = '';
	});

	let charsLeft = $derived(MAX_LENGTH - feedbackText.length);

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

<div class="mx-auto w-full max-w-2xl">
	<SectionIntro description={m.feedback_description()} />

	<form class="flex flex-col gap-6" onsubmit={handleSubmit}>
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

		<FormError message={submitError} />

		<Button type="submit" class="w-full sm:w-auto" disabled={feedbackMutation.isPending}>
			{#if feedbackMutation.isPending}
				<Spinner data-icon="inline-start" />
				{m.common_sending()}
			{:else}
				{m.feedback_submit()}
			{/if}
		</Button>
	</form>
</div>
