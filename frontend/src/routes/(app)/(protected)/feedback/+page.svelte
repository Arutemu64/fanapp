<script lang="ts">
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import SectionIntro from '$lib/components/SectionIntro.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { Alert, Button, Card, Helper, Label, Spinner, Textarea } from 'flowbite-svelte';

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
			const { error, response } = await client.POST('/feedback/', {
				body: {
					text: feedbackText.trim()
				}
			});

			if (error || !response.ok) {
				if (response.status === 401) {
					submitError = 'Нужно войти в аккаунт заново';
				} else if (response.status === 422) {
					submitError = 'Проверьте правильность заполнения поля';
				} else {
					submitError = 'Не удалось отправить отзыв';
				}
				return;
			}

			toastService.add('Спасибо, отзыв отправлен', 'success');
			feedbackText = '';
			feedbackError = '';
		} catch (err) {
			console.error('Failed to submit feedback:', err);
			submitError = 'Произошла непредвиденная ошибка';
		} finally {
			isSending = false;
		}
	}
</script>

<svelte:head>
	<title>Обратная связь · ФАН ФАН</title>
</svelte:head>

<SectionIntro
	description="Расскажи, что нравится в приложении, а что хотелось бы улучшить. Мы читаем каждое сообщение."
/>

<Card class="mx-auto w-full max-w-2xl rounded-2xl p-4 sm:p-6">
	<form class="space-y-6" onsubmit={handleSubmit}>
		<div class="space-y-2">
			<Label for="feedback-text" class="text-gray-900 dark:text-white">Твой отзыв</Label>
			<Textarea
				id="feedback-text"
				name="text"
				rows={6}
				maxlength={MAX_LENGTH}
				placeholder="Поделись впечатлениями, идеями или сообщи о проблеме…"
				bind:value={feedbackText}
				disabled={isSending}
				oninput={handleInput}
				class="w-full rounded-xl"
			/>
			{#if feedbackError}
				<Helper color="red" class="mt-1">{feedbackError}</Helper>
			{:else}
				<Helper class="text-sm text-gray-500 dark:text-gray-400">
					Осталось символов: {charsLeft}
				</Helper>
			{/if}
		</div>

		{#if submitError}
			<Alert color="red">
				{submitError}
			</Alert>
		{/if}

		<Button
			type="submit"
			color="primary"
			class="min-h-11 w-full justify-center sm:w-auto"
			disabled={isSending}
		>
			{#if isSending}
				<Spinner size="4" class="mr-2 fill-white" />
				Отправка…
			{:else}
				Отправить отзыв
			{/if}
		</Button>
	</form>
</Card>
