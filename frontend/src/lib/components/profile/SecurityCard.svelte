<script lang="ts">
	import { PUBLIC_API_URL } from '$env/static/public';
	import { client } from '$lib/api';
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { CurrentUserDTO, UserSocialAccountDTO } from '$lib/types/user';
	import { Alert, Badge, Button, Spinner } from 'flowbite-svelte';
	import {
		EnvelopeSolid,
		ExclamationCircleSolid,
		LinkOutline,
		PaperPlaneOutline,
		ShieldOutline,
		TrashBinOutline
	} from 'flowbite-svelte-icons';
	import ChangePasswordModal from './ChangePasswordModal.svelte';
	import ChangeEmailModal from './ChangeEmailModal.svelte';
	import ProfileCardShell from './ProfileCardShell.svelte';

	interface Props {
		user: CurrentUserDTO;
		socialAccounts: UserSocialAccountDTO[];
		onUpdate?: () => void | Promise<void>;
	}

	let { user, socialAccounts, onUpdate }: Props = $props();

	let changePasswordModalOpen = $state(false);
	let changeEmailModalOpen = $state(false);
	let isRequestingVerification = $state(false);
	let isUnlinkingTelegram = $state(false);
	const toastService = getToastService();
	let emailStatusColor = $derived.by((): 'green' | 'yellow' | 'gray' => {
		if (user.pending_email) return 'yellow';
		if (user.email && user.email_verified_at) return 'green';
		if (user.email) return 'yellow';
		return 'gray';
	});
	let emailStatusLabel = $derived.by(() => {
		if (user.pending_email) return 'Ожидает подтверждения';
		if (user.email && user.email_verified_at) return 'Подтверждена';
		if (user.email) return 'Не подтверждена';
		return 'Не добавлен';
	});

	// Keep the connected Telegram account handy for status text and actions.
	let telegramAccount = $derived(
		socialAccounts.find((socialAccount) => socialAccount.provider === 'telegram') ?? null
	);

	async function requestVerification() {
		if (isRequestingVerification) return;

		isRequestingVerification = true;

		try {
			const { error } = await client.POST('/auth/request-email-verification');

			if (error) {
				toastService.error(error);
				return;
			}

			toastService.add(
				user.pending_email
					? 'Письмо для подтверждения нового адреса отправлено'
					: 'Письмо с подтверждением отправлено',
				'success'
			);
		} catch (err) {
			toastService.error(err);
		} finally {
			isRequestingVerification = false;
		}
	}

	async function handleTelegramUnlink() {
		if (isUnlinkingTelegram || !telegramAccount) return;

		isUnlinkingTelegram = true;

		try {
			const { error } = await client.DELETE('/me/connections/telegram', {});

			if (error) {
				toastService.error(error);
				return;
			}

			toastService.add('Telegram отвязан', 'success');
			await onUpdate?.();
		} catch (err) {
			toastService.error(err);
		} finally {
			isUnlinkingTelegram = false;
		}
	}
</script>

<ProfileCardShell
	title="Способы входа"
	description="Настройте почту, пароль и Telegram для входа и восстановления доступа."
>
	{#snippet icon()}
		<LinkOutline class="h-5 w-5" />
	{/snippet}

	<!-- Compact inner sections keep related account settings easy to scan. -->
	<div class="space-y-3">
		<div class="rounded-lg border border-gray-200 p-3 sm:p-4 dark:border-gray-700">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div class="min-w-0">
					<div class="flex flex-wrap items-center gap-2">
						<EnvelopeSolid class="h-4 w-4 text-gray-500 dark:text-gray-400" />
						<p class="font-medium text-gray-900 dark:text-white">Эл. почта</p>
						<Badge color={emailStatusColor}>{emailStatusLabel}</Badge>
					</div>

					{#if user.email}
						<p class="mt-1.5 text-sm break-all text-gray-500 dark:text-gray-400">{user.email}</p>
						{#if !user.email_verified_at}
							<p class="mt-1 text-xs leading-5 text-gray-500 dark:text-gray-400">
								Подтвердите адрес, чтобы защитить вход и восстановление доступа.
							</p>
						{/if}
					{:else if user.pending_email}
						<p class="mt-1.5 text-sm break-all text-gray-500 dark:text-gray-400">
							{user.pending_email}
						</p>
						<p class="mt-1 text-xs leading-5 text-gray-500 dark:text-gray-400">
							Подтвердите адрес, чтобы сделать его основной почтой для входа и восстановления
							доступа.
						</p>
					{:else}
						<p class="mt-1.5 text-sm leading-5 text-gray-500 dark:text-gray-400">
							Добавьте email для восстановления доступа и важных уведомлений.
						</p>
					{/if}

					{#if user.pending_email}
						<p class="mt-2 text-xs leading-5 text-gray-500 dark:text-gray-400">
							Новый адрес ожидает подтверждения: {user.pending_email}
						</p>
					{/if}
				</div>

				<div class="flex w-full flex-col gap-2 sm:w-auto">
					<Button
						color="alternative"
						size="sm"
						class="min-h-11 w-full sm:w-auto"
						onclick={() => (changeEmailModalOpen = true)}
					>
						{user.email || user.pending_email ? 'Изменить почту' : 'Добавить почту'}
					</Button>

					{#if user.pending_email || (user.email && !user.email_verified_at)}
						<Button
							color="primary"
							size="sm"
							class="min-h-11 w-full sm:w-auto"
							onclick={requestVerification}
							disabled={isRequestingVerification}
						>
							{#if isRequestingVerification}
								<Spinner class="me-2 h-4 w-4" />
								Отправка...
							{:else}
								<EnvelopeSolid class="me-2 h-4 w-4" />
								{user.pending_email ? 'Подтвердить новый адрес' : 'Подтвердить почту'}
							{/if}
						</Button>
					{/if}
				</div>
			</div>
		</div>

		<div class="rounded-lg border border-gray-200 p-3 sm:p-4 dark:border-gray-700">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div class="min-w-0">
					<div class="flex flex-wrap items-center gap-2">
						<ShieldOutline class="h-4 w-4 text-gray-500 dark:text-gray-400" />
						<p class="font-medium text-gray-900 dark:text-white">Пароль</p>
						<Badge color={user.has_password ? 'green' : 'gray'}>
							{user.has_password ? 'Установлен' : 'Не установлен'}
						</Badge>
					</div>

					<p class="mt-1.5 text-sm leading-5 text-gray-500 dark:text-gray-400">
						{#if user.has_password}
							Используйте пароль как дополнительный способ входа.
						{:else}
							Установите пароль, чтобы входить без внешних сервисов.
						{/if}
					</p>
				</div>

				<Button
					color="alternative"
					size="sm"
					class="min-h-11 w-full sm:w-auto"
					onclick={() => (changePasswordModalOpen = true)}
				>
					{user.has_password ? 'Сменить пароль' : 'Установить пароль'}
				</Button>
			</div>
		</div>

		<div class="rounded-lg border border-gray-200 p-3 sm:p-4 dark:border-gray-700">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div class="min-w-0">
					<div class="flex flex-wrap items-center gap-2">
						<PaperPlaneOutline class="h-4 w-4 text-sky-500" />
						<p class="font-medium text-gray-900 dark:text-white">Telegram</p>
						<Badge color={telegramAccount ? 'green' : 'gray'}>
							{telegramAccount ? 'Подключён' : 'Не подключён'}
						</Badge>
					</div>

					{#if telegramAccount}
						<p class="mt-1.5 text-sm text-gray-500 dark:text-gray-400">
							ID аккаунта:
							<span class="font-mono text-gray-700 dark:text-gray-200">
								{telegramAccount.provider_id}
							</span>
						</p>
						<p class="mt-1 text-xs leading-5 text-gray-500 dark:text-gray-400">
							Через Telegram можно быстро входить и получать уведомления от бота.
						</p>
					{:else}
						<p class="mt-1.5 text-sm leading-5 text-gray-500 dark:text-gray-400">
							Подключите Telegram для быстрого входа без пароля.
						</p>
					{/if}
				</div>

				<div class="flex w-full flex-col gap-2 sm:w-auto">
					{#if telegramAccount}
						<!-- Unlink is blocked without email so the user does not lose a recovery path. -->
						<Button
							color="red"
							size="sm"
							class="min-h-11 w-full sm:w-auto"
							disabled={isUnlinkingTelegram || !user.email}
							onclick={handleTelegramUnlink}
						>
							{#if isUnlinkingTelegram}
								<Spinner class="me-2 h-4 w-4" />
								Отвязка...
							{:else}
								<TrashBinOutline class="me-2 h-4 w-4" />
								Отвязать Telegram
							{/if}
						</Button>
					{:else}
						<!-- Use the configured API base so linking works in every deployment setup. -->
						<Button
							href={`${PUBLIC_API_URL}/me/connections/telegram`}
							color="alternative"
							class="min-h-11 w-full sm:w-auto"
						>
							Подключить Telegram
						</Button>
					{/if}
				</div>
			</div>
		</div>
	</div>

	{#if !user.email && !user.pending_email}
		<Alert color="yellow" class="text-sm">
			<div class="flex items-start gap-2">
				<ExclamationCircleSolid class="mt-0.5 h-4 w-4 shrink-0" />
				<p>
					Добавьте почту. Так будет проще восстановить доступ, и только после этого можно безопасно
					отвязать Telegram.
				</p>
			</div>
		</Alert>
	{/if}
</ProfileCardShell>

<ChangePasswordModal
	bind:open={changePasswordModalOpen}
	hasPassword={user.has_password}
	onSuccess={onUpdate}
/>

<ChangeEmailModal
	bind:open={changeEmailModalOpen}
	currentEmail={user.email}
	pendingEmail={user.pending_email}
	onSuccess={onUpdate}
/>
