<script lang="ts">
	import { createApiClient } from '$lib/api';
	import { getApiErrorDetail, getApiFieldError } from '$lib/api/errors';
	import { submitFeedback } from '$lib/api/generated';
	const client = createApiClient();
	import OfflineUnavailableState from '$lib/components/OfflineUnavailableState.svelte';
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import * as Alert from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import * as Field from '$lib/components/ui/field';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Textarea } from '$lib/components/ui/textarea';
	import { getToastService } from '$lib/services/toasts.svelte';

	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const toastService = getToastService();

	const MAX_LENGTH = 2000;

	let feedbackText = $state('');
	let isSending = $state(false);

	let feedbackError = $state('');
	let submitError = $state('');

	let charsLeft = $derived(MAX_LENGTH - feedbackText.length);

	function validateForm() {
		if (!feedbackText.trim()) {
			feedbackError = 'Напиши, чем хочешь поделиться';
			return false;
		}
		feedbackError = '';
		return true;
	}

	function handleInput() {
		if (feedbackError) {
			feedbackError = feedbackText.trim() ? '' : 'Напиши, чем хочешь поделиться';
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';

		if (!validateForm()) {
			return;
		}

		isSending = true;

		try {
			const { error, response } = await submitFeedback({
				client,
				body: {
					text: feedbackText.trim()
				}
			});

			if (error || !response?.ok) {
				const textError = getApiFieldError(error, 'text');
				if (textError) {
					feedbackError = textError;
					return;
				}
				submitError = getApiErrorDetail(error) ?? 'Не удалось отправить отзыв';
				return;
			}

			toastService.add('Спасибо, отзыв отправлен', 'success');
			feedbackText = '';
			feedbackError = '';
		} finally {
			isSending = false;
		}
	}
</script>

<svelte:head>
	<title>Обратная связь · ФАН ФАН</title>
</svelte:head>

{#if data.offlineUnavailable}
	<!-- Submit-only surface with nothing to cache: say so plainly rather than
	     showing a form that can't send. -->
	<OfflineUnavailableState
		title="Обратная связь доступна только онлайн"
		message="Подключись к интернету, чтобы отправить отзыв."
	/>
{:else}
	<div class="mx-auto w-full max-w-2xl">
		<SectionIntro
			description="Расскажи о фестивале или о приложении — что понравилось, а что хотелось бы улучшить. Мы читаем каждое сообщение."
		/>

		<form class="flex flex-col gap-6" onsubmit={handleSubmit}>
			<Field.Field data-invalid={feedbackError ? true : undefined}>
				<Field.FieldLabel for="feedback-text">Твой отзыв</Field.FieldLabel>
				<Textarea
					id="feedback-text"
					name="text"
					rows={6}
					maxlength={MAX_LENGTH}
					placeholder="Поделись впечатлениями о фестивале, идеями по приложению или сообщи о проблеме…"
					bind:value={feedbackText}
					disabled={isSending}
					oninput={handleInput}
					aria-invalid={feedbackError ? true : undefined}
					class="resize-none"
				/>
				{#if feedbackError}
					<Field.FieldError>{feedbackError}</Field.FieldError>
				{:else}
					<Field.FieldDescription>
						Осталось символов: {charsLeft}
					</Field.FieldDescription>
				{/if}
			</Field.Field>

			{#if submitError}
				<Alert.Root variant="destructive">
					<Alert.Description>{submitError}</Alert.Description>
				</Alert.Root>
			{/if}

			<Button type="submit" class="w-full sm:w-auto" disabled={isSending}>
				{#if isSending}
					<Spinner data-icon="inline-start" />
					Отправка…
				{:else}
					Отправить отзыв
				{/if}
			</Button>
		</form>
	</div>
{/if}
