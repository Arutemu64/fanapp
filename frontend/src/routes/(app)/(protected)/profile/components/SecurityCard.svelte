<script lang="ts">
	import { PUBLIC_API_URL } from '$env/static/public';
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { CurrentUserDTO, UserSocialAccountDTO } from '$lib/types/user';
	import { Alert, Badge, Button, Spinner } from 'flowbite-svelte';
	import {
		EnvelopeSolid,
		ExclamationCircleSolid,
		LinkOutline,
		ShieldOutline,
		TrashBinOutline
	} from 'flowbite-svelte-icons';
	import IconTelegram from '~icons/simple-icons/telegram';
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
	let isUnlinkingTelegram = $state(false);
	// Gate the destructive unlink behind a deliberate second tap (inline, no modal).
	let isConfirmingUnlink = $state(false);
	const toastService = getToastService();
	let emailStatusColor = $derived<'green' | 'gray'>(user.email ? 'green' : 'gray');
	let emailStatusLabel = $derived(user.email ? 'Подтверждена' : 'Не добавлена');

	// Keep the connected Telegram account handy for status text and actions.
	let telegramAccount = $derived(
		socialAccounts.find((socialAccount) => socialAccount.provider === 'telegram') ?? null
	);

	async function handleTelegramUnlink() {
		if (isUnlinkingTelegram || !telegramAccount) return;

		isUnlinkingTelegram = true;

		try {
			const { error, response } = await client.DELETE('/me/connections/telegram', {});

			if (error || !response.ok) {
				toastService.error(error);
				return;
			}

			toastService.add('Telegram отвязан', 'success');
			await onUpdate?.();
		} catch (err) {
			toastService.error(err);
		} finally {
			isUnlinkingTelegram = false;
			// Drop back to the resting state whether it succeeded or failed.
			isConfirmingUnlink = false;
		}
	}
</script>

<ProfileCardShell
	title="Способы входа"
	description="Настрой почту, пароль и Telegram для входа и восстановления доступа."
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
						<Badge color={emailStatusColor} border>{emailStatusLabel}</Badge>
					</div>

					{#if user.email}
						<p class="mt-1.5 text-sm break-all text-gray-500 dark:text-gray-400">{user.email}</p>
					{:else}
						<p class="mt-1.5 text-sm leading-5 text-gray-500 dark:text-gray-400">
							Добавь email для восстановления доступа и важных уведомлений.
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
						{user.email ? 'Изменить' : 'Добавить'}
					</Button>
				</div>
			</div>
		</div>

		<div class="rounded-lg border border-gray-200 p-3 sm:p-4 dark:border-gray-700">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div class="min-w-0">
					<div class="flex flex-wrap items-center gap-2">
						<ShieldOutline class="h-4 w-4 text-gray-500 dark:text-gray-400" />
						<p class="font-medium text-gray-900 dark:text-white">Пароль</p>
						<Badge color={user.has_password ? 'green' : 'gray'} border>
							{user.has_password ? 'Установлен' : 'Не установлен'}
						</Badge>
					</div>

					<p class="mt-1.5 text-sm leading-5 text-gray-500 dark:text-gray-400">
						{#if user.has_password}
							Используй пароль как дополнительный способ входа.
						{:else}
							Установи пароль, чтобы входить без внешних сервисов.
						{/if}
					</p>
				</div>

				<Button
					color="alternative"
					size="sm"
					class="min-h-11 w-full sm:w-auto"
					onclick={() => (changePasswordModalOpen = true)}
				>
					{user.has_password ? 'Изменить' : 'Установить'}
				</Button>
			</div>
		</div>

		<div class="rounded-lg border border-gray-200 p-3 sm:p-4 dark:border-gray-700">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div class="min-w-0">
					<div class="flex flex-wrap items-center gap-2">
						<IconTelegram class="h-4 w-4 text-sky-500" />
						<p class="font-medium text-gray-900 dark:text-white">Telegram</p>
						<Badge color={telegramAccount ? 'green' : 'gray'} border>
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
						<p class="mt-1 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
							Через Telegram можно быстро входить и получать уведомления от бота.
						</p>
					{:else}
						<p class="mt-1.5 text-sm leading-5 text-gray-500 dark:text-gray-400">
							Подключи Telegram для быстрого входа без пароля.
						</p>
					{/if}
				</div>

				<div class="flex w-full flex-col gap-2 sm:w-auto">
					{#if telegramAccount}
						{#if isConfirmingUnlink}
							<!-- Inline confirm: a destructive account change should cost a deliberate second tap. -->
							<p class="text-sm font-medium text-gray-900 sm:text-right dark:text-white">
								Отвязать Telegram?
							</p>
							<div class="flex gap-2">
								<Button
									color="red"
									size="sm"
									class="min-h-11 flex-1 sm:flex-initial"
									disabled={isUnlinkingTelegram || !user.email}
									onclick={handleTelegramUnlink}
								>
									{#if isUnlinkingTelegram}
										<Spinner class="me-2 h-4 w-4" />
										Отвязка…
									{:else}
										<TrashBinOutline class="me-2 h-4 w-4" />
										Отвязать
									{/if}
								</Button>
								<Button
									color="alternative"
									size="sm"
									class="min-h-11 flex-1 sm:flex-initial"
									disabled={isUnlinkingTelegram}
									onclick={() => (isConfirmingUnlink = false)}
								>
									Отмена
								</Button>
							</div>
						{:else}
							<!-- Unlink is blocked without email so the user does not lose a recovery path. -->
							<Button
								color="red"
								size="sm"
								class="min-h-11 w-full sm:w-auto"
								disabled={!user.email}
								onclick={() => (isConfirmingUnlink = true)}
							>
								<TrashBinOutline class="me-2 h-4 w-4" />
								Отвязать
							</Button>
						{/if}
					{:else}
						<!-- Use the configured API base so linking works in every deployment setup. -->
						<Button
							href={`${PUBLIC_API_URL}/me/connections/telegram`}
							color="alternative"
							class="min-h-11 w-full sm:w-auto"
						>
							Подключить
						</Button>
					{/if}
				</div>
			</div>
		</div>
	</div>

	{#if !user.email}
		<Alert color="yellow" class="text-sm">
			<div class="flex items-start gap-2">
				<ExclamationCircleSolid class="mt-0.5 h-4 w-4 shrink-0" />
				<p>
					Добавь почту. Так будет проще восстановить доступ, и только после этого можно безопасно
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

<ChangeEmailModal bind:open={changeEmailModalOpen} currentEmail={user.email} onSuccess={onUpdate} />
