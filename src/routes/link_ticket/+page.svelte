<script lang="ts">
	import { Button, Input, Label, Alert, Card, Spinner } from 'flowbite-svelte';
	import { CheckCircleOutline } from 'flowbite-svelte-icons';

	let ticketNumber = $state('');
	let error = $state('');
	let success = $state(false);
	let isSubmitting = $state(false);

	const validTickets = ['TK-123456', 'FAN-2024-001'];

	function validateTicket(number: string): boolean {
		return validTickets.includes(number.toUpperCase());
	}

	async function handleSubmit() {
		error = '';
		success = false;

		if (!ticketNumber.trim()) {
			error = 'Введите номер билета';
			return;
		}

		isSubmitting = true;

		// Simulate API call
		await new Promise((resolve) => setTimeout(resolve, 1000));

		if (validateTicket(ticketNumber)) {
			success = true;
			ticketNumber = '';
		} else {
			error = 'Неверный номер билета. Проверьте правильность ввода.';
		}

		isSubmitting = false;
	}
</script>

<svelte:head>
	<title>Привязка билета</title>
</svelte:head>

<div class="mb-4 sm:mb-6">
	<h1 class="mb-1 text-lg font-bold text-gray-900 sm:mb-2 sm:text-xl dark:text-white">
		Привязка билета
	</h1>
	<p class="text-xs text-gray-500 sm:text-sm dark:text-gray-400">
		Привяжите ваш билет для доступа к полному функционалу приложения
	</p>
</div>

<div class="grid items-start gap-4 sm:gap-4 lg:grid-cols-2 lg:gap-6">
	<Card class="p-4">
		<h2
			class="mb-3 text-center text-sm font-semibold text-gray-900 sm:mb-4 sm:text-base dark:text-white"
		>
			Преимущества привязки билета
		</h2>
		<ul class="space-y-4">
			<li class="flex items-start gap-2 sm:gap-3">
				<div
					class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-100 sm:h-7 sm:w-7 dark:bg-primary-900"
				>
					<CheckCircleOutline
						class="h-3.5 w-3.5 text-primary-600 sm:h-4 sm:w-4 dark:text-primary-400"
					/>
				</div>
				<div>
					<span class="text-xs font-medium text-gray-900 sm:text-sm dark:text-white"
						>Участие в голосовании</span
					>
					<p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
						Голосуйте за лучших участников мероприятия
					</p>
				</div>
			</li>

			<li class="flex items-start gap-2 sm:gap-3">
				<div
					class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-100 sm:h-7 sm:w-7 dark:bg-primary-900"
				>
					<CheckCircleOutline
						class="h-3.5 w-3.5 text-primary-600 sm:h-4 sm:w-4 dark:text-primary-400"
					/>
				</div>
				<div>
					<span class="text-xs font-medium text-gray-900 sm:text-sm dark:text-white"
						>Выполнение квестов</span
					>
					<p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
						Участвуйте в квестах и получайте награды
					</p>
				</div>
			</li>

			<li class="flex items-start gap-2 sm:gap-3">
				<div
					class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-100 sm:h-7 sm:w-7 dark:bg-primary-900"
				>
					<CheckCircleOutline
						class="h-3.5 w-3.5 text-primary-600 sm:h-4 sm:w-4 dark:text-primary-400"
					/>
				</div>
				<div>
					<span class="text-xs font-medium text-gray-900 sm:text-sm dark:text-white"
						>Эксклюзивные материалы</span
					>
					<p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
						Получите доступ к уникальному контенту
					</p>
				</div>
			</li>
		</ul>
	</Card>

	<Card class="p-3 sm:p-4 lg:p-6">
		<h2
			class="mb-3 text-center text-sm font-semibold text-gray-900 sm:mb-4 sm:text-base dark:text-white"
		>
			Введите номер билета
		</h2>

		{#if error}
			<Alert color="red" class="mb-3 text-xs sm:mb-4 sm:text-sm">
				{error}
			</Alert>
		{/if}

		{#if success}
			<Alert color="green" class="mb-3 text-xs sm:mb-4 sm:text-sm">
				Билет успешно привязан! Теперь вам доступны все функции приложения.
			</Alert>
		{/if}

		<form
			onsubmit={(e) => {
				e.preventDefault();
				handleSubmit();
			}}
		>
			<div class="mb-3 sm:mb-4">
				<Label for="ticket-number" class="mb-1.5 block text-xs sm:mb-2 sm:text-sm">
					Номер билета
				</Label>
				<Input
					id="ticket-number"
					bind:value={ticketNumber}
					placeholder="Например: TK-123456"
					disabled={isSubmitting}
					size="md"
				/>
				<p class="mt-1.5 text-xs text-gray-500 sm:mt-2 sm:text-sm dark:text-gray-400">
					Номер указан на вашем билете или в электронном подтверждении
				</p>
			</div>

			<Button type="submit" class="w-full" disabled={isSubmitting} size="md">
				{#if isSubmitting}
					<Spinner class="me-2 h-4 w-4 sm:h-5 sm:w-5" />
					Проверка...
				{:else}
					Привязать билет
				{/if}
			</Button>
		</form>

		<div class="mt-3 rounded-lg bg-gray-50 p-2 sm:mt-4 sm:p-3 lg:p-4 dark:bg-gray-700/50">
			<p class="text-center text-xs text-gray-500 dark:text-gray-400">
				Для тестирования: <span class="font-mono font-medium">TK-123456</span>,
				<span class="font-mono font-medium">FAN-2024-001</span>
			</p>
		</div>
	</Card>
</div>
