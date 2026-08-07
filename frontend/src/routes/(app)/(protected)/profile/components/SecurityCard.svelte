<script lang="ts">
	import type { CurrentUserDTO } from '$lib/types/user';

	import { PUBLIC_API_URL } from '$env/static/public';
	import { createApiClient } from '$lib/api';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { Alert, Badge, Button } from 'flowbite-svelte';
	import {
		EnvelopeSolid,
		ExclamationCircleSolid,
		LinkOutline,
		ShieldOutline
	} from 'flowbite-svelte-icons';
	import IconTelegram from '~icons/simple-icons/telegram';
	import IconVk from '~icons/simple-icons/vk';

	import ChangeEmailModal from './ChangeEmailModal.svelte';
	import ChangePasswordModal from './ChangePasswordModal.svelte';
	import ProfileCardShell from './ProfileCardShell.svelte';
	import SocialConnectionRow from './SocialConnectionRow.svelte';

	const client = createApiClient();

	interface Props {
		user: CurrentUserDTO;
		onUpdate?: () => void | Promise<void>;
	}

	let { user, onUpdate }: Props = $props();

	let changePasswordModalOpen = $state(false);
	let changeEmailModalOpen = $state(false);
	const toastService = getToastService();
	let emailStatusColor = $derived<'green' | 'gray'>(user.email ? 'green' : 'gray');
	let emailStatusLabel = $derived(user.email ? 'Подтверждена' : 'Не добавлена');

	let telegramAccount = $derived(
		user.social_identities.find((si) => si.provider === 'telegram') ?? null
	);
	let vkAccount = $derived(user.social_identities.find((si) => si.provider === 'vk') ?? null);

	// The unlink DELETEs differ only in path + copy; SocialConnectionRow owns the
	// confirm-and-loading UI and calls one of these to perform the action.
	async function unlinkTelegram() {
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
		}
	}

	async function unlinkVk() {
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

		<SocialConnectionRow
			label="Telegram"
			connected={telegramAccount !== null}
			connectedDescription="Через Telegram можно быстро входить и получать уведомления от бота."
			notConnectedDescription="Подключи Telegram для быстрого входа без пароля."
			connectHref={`${PUBLIC_API_URL}/me/connections/telegram`}
			unlinkPrompt="Отвязать Telegram?"
			hasEmail={Boolean(user.email)}
			onUnlink={unlinkTelegram}
		>
			{#snippet icon()}
				<IconTelegram class="h-4 w-4 text-gray-500 dark:text-gray-400" />
			{/snippet}
		</SocialConnectionRow>

		<SocialConnectionRow
			label="VK ID"
			connected={vkAccount !== null}
			connectedDescription="Через VK ID можно быстро входить без пароля."
			notConnectedDescription="Подключи VK ID для быстрого входа без пароля."
			connectHref={`${PUBLIC_API_URL}/me/connections/vk`}
			unlinkPrompt="Отвязать VK ID?"
			hasEmail={Boolean(user.email)}
			onUnlink={unlinkVk}
		>
			{#snippet icon()}
				<IconVk class="h-4 w-4 text-gray-500 dark:text-gray-400" />
			{/snippet}
		</SocialConnectionRow>
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
