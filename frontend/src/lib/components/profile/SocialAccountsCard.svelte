<script lang="ts">
	import { client } from '$lib/api';
	import type { components } from '$lib/api/v1';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import type { CurrentUserDTO, UserSocialAccountDTO } from '$lib/types/user';
	import { Alert, Badge, Button, Card, Spinner } from 'flowbite-svelte';
	import { LinkOutline, PaperPlaneOutline, TrashBinOutline } from 'flowbite-svelte-icons';
	import type { Attachment } from 'svelte/attachments';

	interface Props {
		user: CurrentUserDTO;
		socialAccounts: UserSocialAccountDTO[];
		onUpdate?: () => void | Promise<void>;
	}

	type TelegramAuthPayload = components['schemas']['LinkTelegramAccountCommand'];
	type TelegramCallbackWindow = Window &
		Record<string, ((user: TelegramAuthPayload) => void) | undefined>;

	const TELEGRAM_BOT_NAME = 'fanfanalpha_bot';

	let { user, socialAccounts, onUpdate }: Props = $props();
	const uid = $props.id();
	const callbackName = `telegramProfileAuth_${uid.replaceAll('-', '_')}`;
	const toastService = getToastService();

	let isLinking = $state(false);
	let isUnlinking = $state(false);
	let linkError = $state('');

	let telegramAccount = $derived(
		socialAccounts.find((socialAccount) => socialAccount.provider === 'telegram') ?? null
	);

	const telegramWidget: Attachment<HTMLDivElement> = (node) => {
		const callbackWindow = window as unknown as TelegramCallbackWindow;
		callbackWindow[callbackName] = handleTelegramLink;

		// Telegram injects its own button markup, so we isolate that work inside an action.
		const script = document.createElement('script');
		script.src = 'https://telegram.org/js/telegram-widget.js?22';
		script.setAttribute('data-telegram-login', TELEGRAM_BOT_NAME);
		script.setAttribute('data-size', 'large');
		script.setAttribute('data-radius', '12');
		script.setAttribute('data-onauth', `${callbackName}(user)`);
		script.setAttribute('data-request-access', 'write');
		script.async = true;
		node.appendChild(script);

		return () => {
			delete callbackWindow[callbackName];
			node.replaceChildren();
		};
	};

	async function handleTelegramLink(telegramUser: TelegramAuthPayload) {
		if (isLinking) return;

		linkError = '';
		isLinking = true;

		const { error, response } = await client.POST('/users/me/social-accounts/telegram', {
			body: telegramUser
		});

		isLinking = false;

		if (error) {
			const errorMessage =
				typeof error.detail === 'string' ? error.detail : 'Не удалось привязать Telegram';

			// Keep the conflict visible inside the card so the user understands why linking failed.
			if (response.status === 409) {
				linkError = errorMessage;
				return;
			}

			toastService.error(error);
			return;
		}

		toastService.add('Telegram подключён', 'success');
		await onUpdate?.();
	}

	async function handleTelegramUnlink() {
		if (isUnlinking) return;

		linkError = '';
		isUnlinking = true;

		const { error } = await client.DELETE('/users/me/social-accounts/telegram');

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

		<div
			class="rounded-lg border border-gray-200 p-4 dark:border-gray-700"
		>
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
				<div class="mt-4 space-y-3">
					<div {@attach telegramWidget} class="min-h-11"></div>

					{#if isLinking}
						<div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
							<Spinner class="h-4 w-4" />
							<span>Подключаем Telegram...</span>
						</div>
					{/if}
				</div>
			{/if}
		</div>

		{#if telegramAccount && !user.email}
			<Alert color="yellow" class="mt-4">
				Сначала добавьте email, потом можно отвязать Telegram.
			</Alert>
		{/if}

		{#if linkError}
			<Alert color="red" class="mt-4">
				{linkError}
			</Alert>
		{/if}
	</div>
</Card>
