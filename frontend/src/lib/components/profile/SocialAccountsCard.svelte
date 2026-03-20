<script lang="ts">
	import { PUBLIC_API_URL } from '$env/static/public';
	import { client } from '$lib/api';
	import { getToastService } from '$lib/services/toasts.svelte';
	import type { CurrentUserDTO, UserSocialAccountDTO } from '$lib/types/user';
	import { Alert, Badge, Button, Spinner } from 'flowbite-svelte';
	import { LinkOutline, PaperPlaneOutline, TrashBinOutline } from 'flowbite-svelte-icons';
	import ProfileCardShell from './ProfileCardShell.svelte';

	interface Props {
		user: CurrentUserDTO;
		socialAccounts: UserSocialAccountDTO[];
		onUpdate?: () => void | Promise<void>;
	}

	let { user, socialAccounts, onUpdate }: Props = $props();
	const toastService = getToastService();

	let isUnlinking = $state(false);

	let telegramAccount = $derived(
		socialAccounts.find((socialAccount) => socialAccount.provider === 'telegram') ?? null
	);

	async function handleTelegramUnlink() {
		if (isUnlinking) return;

		isUnlinking = true;

		const { error } = await client.DELETE('/me/connections/telegram', {});

		isUnlinking = false;

		if (error) {
			toastService.error(error);
			return;
		}

		toastService.add('Telegram отвязан', 'success');
		await onUpdate?.();
	}
</script>

<ProfileCardShell
	title="Соцсети"
	description="Подключайте внешние аккаунты для быстрого входа и будущих уведомлений."
>
	{#snippet icon()}
		<LinkOutline class="h-5 w-5" />
	{/snippet}

	<div class="rounded-lg border border-gray-200 p-3 sm:p-4 dark:border-gray-700">
		<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
			<div class="min-w-0">
				<div class="flex items-center gap-2">
					<PaperPlaneOutline class="h-5 w-5 text-sky-500" />
					<p class="font-medium text-gray-900 dark:text-white">Telegram</p>
					<Badge color={telegramAccount ? 'green' : 'gray'}>
						{telegramAccount ? 'Подключён' : 'Не подключён'}
					</Badge>
				</div>

				{#if telegramAccount}
					<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
						ID аккаунта:
						<span class="font-mono text-gray-700 dark:text-gray-200">
							{telegramAccount.provider_id}
						</span>
					</p>
					<p class="mt-1 text-xs leading-5 text-gray-500 dark:text-gray-400">
						Используйте Telegram для быстрого входа и сообщений от бота.
					</p>
				{:else}
					<p class="mt-2 text-sm leading-5 text-gray-500 dark:text-gray-400">
						Пока доступно подключение только через Telegram.
					</p>
				{/if}
			</div>

			<div class="flex w-full flex-col gap-2 sm:w-auto">
				{#if telegramAccount}
					<Button
						color="red"
						size="sm"
						class="min-h-11 w-full sm:w-auto"
						disabled={isUnlinking || !user.email}
						onclick={handleTelegramUnlink}
					>
						{#if isUnlinking}
							<Spinner class="me-2 h-4 w-4" />
							Отвязка...
						{:else}
							<TrashBinOutline class="me-2 h-4 w-4" />
							Отвязать Telegram
						{/if}
					</Button>
				{:else}
					<!-- Use the configured API base so linking works outside the local /api proxy too. -->
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

	{#if telegramAccount && !user.email}
		<Alert color="yellow" class="text-sm">
			Сначала добавьте email, потом можно отвязать Telegram.
		</Alert>
	{/if}
</ProfileCardShell>
