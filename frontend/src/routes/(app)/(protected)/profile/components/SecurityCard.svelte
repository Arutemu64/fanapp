<script lang="ts">
	import type { CurrentUserDTO } from '$lib/types/user';

	import { PUBLIC_API_URL } from '$env/static/public';
	import { createApiClient } from '$lib/api';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { Alert, Badge, Button, Spinner } from 'flowbite-svelte';
	import {
		EnvelopeSolid,
		ExclamationCircleSolid,
		LinkOutline,
		ShieldOutline,
		TrashBinOutline
	} from 'flowbite-svelte-icons';
	import IconTelegram from '~icons/simple-icons/telegram';
	import IconVk from '~icons/simple-icons/vk';

	import ChangeEmailModal from './ChangeEmailModal.svelte';
	import ChangePasswordModal from './ChangePasswordModal.svelte';
	import ProfileCardShell from './ProfileCardShell.svelte';

	const client = createApiClient();

	interface Props {
		user: CurrentUserDTO;
		onUpdate?: () => void | Promise<void>;
	}

	let { user, onUpdate }: Props = $props();

	let changePasswordModalOpen = $state(false);
	let changeEmailModalOpen = $state(false);
	let isUnlinkingTelegram = $state(false);
	let isUnlinkingVk = $state(false);
	// Gate destructive unlinks behind a deliberate second tap (inline, no modal).
	let isConfirmingTelegramUnlink = $state(false);
	let isConfirmingVkUnlink = $state(false);
	const toastService = getToastService();
	let emailStatusColor = $derived<'green' | 'gray'>(user.email ? 'green' : 'gray');
	let emailStatusLabel = $derived(user.email ? 'Подтверждена' : 'Не добавлена');

	let telegramAccount = $derived(
		user.social_identities.find((si) => si.provider === 'telegram') ?? null
	);
	let vkAccount = $derived(user.social_identities.find((si) => si.provider === 'vk') ?? null);

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
			isConfirmingTelegramUnlink = false;
		}
	}

	async function handleVkUnlink() {
		if (isUnlinkingVk || !vkAccount) return;

		isUnlinkingVk = true;

		try {
			const { error, response } = await client.DELETE('/me/connections/vk', {});

			if (error || !response.ok) {
				toastService.error(error);
				return;
			}

			toastService.add('VK отвязан', 'success');
			await onUpdate?.();
		} catch (err) {
			toastService.error(err);
		} finally {
			isUnlinkingVk = false;
			isConfirmingVkUnlink = false;
		}
	}
</script>

<ProfileCardShell
	title="Способы входа"
	description="Настрой почту, пароль и привязки для входа и восстановления доступа."
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
						<p class="mt-1.5 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
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
						{#if isConfirmingTelegramUnlink}
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
										<Spinner class="me-2 h-4 w-4 fill-white" />
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
									onclick={() => (isConfirmingTelegramUnlink = false)}
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
								onclick={() => (isConfirmingTelegramUnlink = true)}
							>
								<TrashBinOutline class="me-2 h-4 w-4" />
								Отвязать
							</Button>
						{/if}
					{:else}
						<Button
							href={`${PUBLIC_API_URL}/me/connections/telegram`}
							color="alternative"
							class="min-h-11 w-full sm:w-auto"
						>
							<IconTelegram class="me-2 h-4 w-4 text-sky-500" />
							Подключить
						</Button>
					{/if}
				</div>
			</div>
		</div>

		<div class="rounded-lg border border-gray-200 p-3 sm:p-4 dark:border-gray-700">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div class="min-w-0">
					<div class="flex flex-wrap items-center gap-2">
						<IconVk class="h-4 w-4 text-[#0077FF]" />
						<p class="font-medium text-gray-900 dark:text-white">VK ID</p>
						<Badge color={vkAccount ? 'green' : 'gray'} border>
							{vkAccount ? 'Подключён' : 'Не подключён'}
						</Badge>
					</div>

					{#if vkAccount}
						<p class="mt-1.5 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
							Через VK ID можно быстро входить без пароля.
						</p>
					{:else}
						<p class="mt-1.5 text-sm leading-5 text-gray-500 dark:text-gray-400">
							Подключи VK ID для быстрого входа без пароля.
						</p>
					{/if}
				</div>

				<div class="flex w-full flex-col gap-2 sm:w-auto">
					{#if vkAccount}
						{#if isConfirmingVkUnlink}
							<p class="text-sm font-medium text-gray-900 sm:text-right dark:text-white">
								Отвязать VK ID?
							</p>
							<div class="flex gap-2">
								<Button
									color="red"
									size="sm"
									class="min-h-11 flex-1 sm:flex-initial"
									disabled={isUnlinkingVk || !user.email}
									onclick={handleVkUnlink}
								>
									{#if isUnlinkingVk}
										<Spinner class="me-2 h-4 w-4 fill-white" />
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
									disabled={isUnlinkingVk}
									onclick={() => (isConfirmingVkUnlink = false)}
								>
									Отмена
								</Button>
							</div>
						{:else}
							<Button
								color="red"
								size="sm"
								class="min-h-11 w-full sm:w-auto"
								disabled={!user.email}
								onclick={() => (isConfirmingVkUnlink = true)}
							>
								<TrashBinOutline class="me-2 h-4 w-4" />
								Отвязать
							</Button>
						{/if}
					{:else}
						<Button
							href={`${PUBLIC_API_URL}/me/connections/vk`}
							color="alternative"
							class="min-h-11 w-full sm:w-auto"
						>
							<IconVk class="me-2 h-4 w-4 text-[#0077FF]" />
							Подключить
						</Button>
					{/if}
				</div>
			</div>
		</div>
	</div>

	{#if !user.email}
		<Alert color="yellow">
			<div class="flex items-start gap-2">
				<ExclamationCircleSolid class="mt-0.5 h-4 w-4 shrink-0" />
				<p>
					Добавь почту. Так будет проще восстановить доступ, и только после этого можно безопасно
					отвязать привязки.
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
