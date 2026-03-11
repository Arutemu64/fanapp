<script lang="ts">
	import { client } from '$lib/api';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import type { CurrentUserDTO, UserSocialAccountDTO } from '$lib/types/user';
	import { Alert, Badge, Button, Card, Spinner } from 'flowbite-svelte';
	import { LinkOutline, PaperPlaneOutline, TrashBinOutline } from 'flowbite-svelte-icons';

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

		const { error } = await client.DELETE('/me/unlink/telegram', {});

		isUnlinking = false;

		if (error) {
			toastService.error(error);
			return;
		}

		toastService.add('Telegram отвязан', 'success');
		await onUpdate?.();
	}
</script>

<Card class="w-full max-w-none rounded-lg bg-white shadow dark:bg-gray-800">
	<div class="p-6">
		<div class="mb-4 flex items-center gap-2">
			<LinkOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Соцсети</h3>
		</div>

		<p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
			Подключайте внешние аккаунты для быстрого входа и будущих уведомлений.
		</p>

		<div class="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
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
					{:else}
						<p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
							Пока доступно подключение только через Telegram.
						</p>
					{/if}
				</div>

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
							Отвязать
						{/if}
					</Button>
				{/if}
			</div>

			{#if !telegramAccount}
				<div class="mt-4">
					<!-- Backend starts the Telegram linking flow after this redirect. -->
					<Button
						href="/api/me/link/telegram"
						color="alternative"
						class="min-h-11 w-full sm:w-auto"
					>
						Подключить Telegram
					</Button>
				</div>
			{/if}
		</div>

		{#if telegramAccount && !user.email}
			<Alert color="yellow" class="mt-4">
				Сначала добавьте email, потом можно отвязать Telegram.
			</Alert>
		{/if}

	</div>
</Card>
