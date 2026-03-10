<script lang="ts">
	import { Card, Button, Alert } from 'flowbite-svelte';
	import { ShieldOutline, EnvelopeSolid, ExclamationCircleSolid } from 'flowbite-svelte-icons';
	import ChangePasswordModal from './ChangePasswordModal.svelte';
	import ChangeEmailModal from './ChangeEmailModal.svelte';
	import type { CurrentUserDTO } from '$lib/types/user';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import { client } from '$lib/api';

	interface Props {
		user: CurrentUserDTO;
		onPasswordChange?: () => void;
		onEmailChange?: () => void;
	}

	let { user, onPasswordChange, onEmailChange }: Props = $props();

	let changePasswordModalOpen = $state(false);
	let changeEmailModalOpen = $state(false);
	let isRequestingVerification = $state(false);
	const toastService = getToastService();

	async function requestVerification() {
		if (isRequestingVerification) return;
		isRequestingVerification = true;
		try {
			const { error } = await client.POST('/auth/request-email-verification');
			if (error) {
				toastService.error(error);
			} else {
				toastService.add('Письмо с подтверждением отправлено', 'success');
			}
		} catch (err) {
			toastService.error(err);
		} finally {
			isRequestingVerification = false;
		}
	}
</script>

<Card class="w-full max-w-none rounded-lg bg-white shadow dark:bg-gray-800">
	<div class="p-6">
		<div class="mb-4 flex items-center gap-2">
			<ShieldOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Безопасность</h3>
		</div>

		<p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
			Управление настройками безопасности вашей учетной записи.
		</p>

		<div class="flex flex-col gap-4 sm:flex-row sm:items-center">
			<Button
				color="alternative"
				size="sm"
				class="w-full sm:w-auto"
				onclick={() => (changePasswordModalOpen = true)}
			>
				{user.has_password ? 'Сменить пароль' : 'Установить пароль'}
			</Button>

			<Button
				color="alternative"
				size="sm"
				class="w-full sm:w-auto"
				onclick={() => (changeEmailModalOpen = true)}
			>
				{user.email ? 'Изменить email' : 'Добавить email'}
			</Button>

			{#if user.email && !user.is_verified}
				<Button
					color="primary"
					size="sm"
					class="w-full sm:w-auto"
					onclick={requestVerification}
					disabled={isRequestingVerification}
				>
					<EnvelopeSolid class="mr-2 h-4 w-4" />
					Подтвердить email
				</Button>
			{/if}
		</div>

		{#if !user.email}
			<Alert color="yellow" class="mt-4">
				<div class="flex items-start gap-2">
					<ExclamationCircleSolid class="mt-0.5 h-4 w-4 shrink-0" />
					<p>
						<span class="font-medium">Внимание!</span> К вашему аккаунту не привязан email. Мы настоятельно
						рекомендуем добавить его для защиты вашей учетной записи.
					</p>
				</div>
			</Alert>
		{/if}
	</div>
</Card>

<ChangePasswordModal
	bind:open={changePasswordModalOpen}
	hasPassword={user.has_password}
	onSuccess={onPasswordChange}
/>

<ChangeEmailModal
	bind:open={changeEmailModalOpen}
	currentEmail={user.email}
	onSuccess={onEmailChange}
/>
