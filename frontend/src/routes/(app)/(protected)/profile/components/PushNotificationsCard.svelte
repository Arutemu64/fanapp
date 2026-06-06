<script lang="ts">
	import { Button, Modal, Toggle } from 'flowbite-svelte';
	import { ArrowDownToBracketOutline, BellOutline, BellSolid } from 'flowbite-svelte-icons';
	import { createApiClient } from '$lib/api';
	const client = createApiClient();
	import { getPwaService } from '$lib/services/pwa.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { env } from '$env/dynamic/public';
	import { onMount } from 'svelte';
	import type { CurrentUserDTO, UserSocialAccountDTO } from '$lib/types/user';
	import type { components } from '$lib/api/v1';
	import ProfileCardShell from './ProfileCardShell.svelte';

	interface Props {
		user: CurrentUserDTO;
		socialAccounts?: UserSocialAccountDTO[];
		pushSubscriptions?: components['schemas']['PushSubscriptionDTO'][];
		onSettingsUpdate?: () => void;
	}

	let { user, socialAccounts = [], pushSubscriptions = [], onSettingsUpdate }: Props = $props();

	let isSubscribed = $state(false);
	const toastService = getToastService();
	let isLoading = $state(true);
	let receiveAll = $derived(user.settings.receive_all_announcements);
	let receiveTelegram = $derived(user.settings.receive_telegram_notifications);
	let isSavingSettings = $state(false);
	let isSendingTest = $state(false);
	const pwa = getPwaService();
	let showIosPwaModal = $state(false);
	let hasTelegramAccount = $derived(
		socialAccounts.some((socialAccount) => socialAccount.provider === 'telegram')
	);

	// Convert base64 VAPID key to Uint8Array required by pushManager.
	function urlBase64ToUint8Array(base64String: string) {
		const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
		const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');

		const rawData = window.atob(base64);
		const outputArray = new Uint8Array(rawData.length);

		for (let i = 0; i < rawData.length; ++i) {
			outputArray[i] = rawData.charCodeAt(i);
		}
		return outputArray;
	}

	async function checkSubscription() {
		try {
			if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
				isLoading = false;
				return;
			}
			const registration = await navigator.serviceWorker.ready;
			const subscription = await registration.pushManager.getSubscription();

			if (!subscription) {
				isSubscribed = false;
				return;
			}

			// Compare the browser subscription with what the server knows about this device.
			const serverSub = pushSubscriptions.find((s) => s.endpoint === subscription.endpoint);

			if (serverSub) {
				isSubscribed = true;
			} else {
				isSubscribed = false;
			}
		} catch (error) {
			console.error('Error checking push subscription:', error);
		} finally {
			isLoading = false;
		}
	}

	onMount(() => {
		void checkSubscription();
	});

	async function toggleSubscription() {
		if (isSubscribed) {
			try {
				isLoading = true;
				const registration = await navigator.serviceWorker.ready;
				const subscription = await registration.pushManager.getSubscription();
				if (subscription) {
					// Remove the matching subscription on the backend before unsubscribing locally.
					const { error, response } = await client.DELETE('/push/', {
						body: {
							endpoint: subscription.endpoint
						}
					});

					if (error || !response.ok) {
						console.error('Failed to remove subscription from server:', error);
					}

					await subscription.unsubscribe();
					isSubscribed = false;
					onSettingsUpdate?.();
					toastService.add('Уведомления отключены для этого устройства', 'success');
				}
			} catch (e) {
				console.error('Failed to unsubscribe', e);
				toastService.add('Не удалось отключить уведомления', 'error');
			} finally {
				isLoading = false;
			}
			return;
		}

		if (pwa.isIOS && !pwa.isInstalled) {
			showIosPwaModal = true;
			return;
		}

		isLoading = true;
		try {
			if (typeof Notification === 'undefined') {
				toastService.add('Твой браузер не поддерживает уведомления', 'error');
				return;
			}

			if (Notification.permission === 'default') {
				const permission = await Notification.requestPermission();
				if (permission !== 'granted') {
					toastService.add('Доступ к уведомлениям отклонен', 'error');
					return;
				}
			} else if (Notification.permission === 'denied') {
				toastService.add('Уведомления заблокированы в настройках браузера', 'error');
				return;
			}

			const registration = await navigator.serviceWorker.ready;

			const subscription = await registration.pushManager.subscribe({
				userVisibleOnly: true,
				applicationServerKey: urlBase64ToUint8Array(env.PUBLIC_VAPID_KEY)
			});

			const subJson = subscription.toJSON();
			const endpoint = subJson.endpoint;
			const p256dh = subJson.keys?.p256dh;
			const auth = subJson.keys?.auth;

			if (!endpoint || !p256dh || !auth) {
				toastService.add('Не удалось подготовить данные устройства для подписки', 'error');
				await subscription.unsubscribe();
				return;
			}

			const { error, response } = await client.POST('/push/', {
				body: {
					endpoint,
					p256dh,
					auth
				}
			});

			if (error || !response.ok) {
				console.error('API Error:', error);
				toastService.add('Ошибка при подписке на уведомления', 'error');
				await subscription.unsubscribe();
				return;
			}

			isSubscribed = true;
			onSettingsUpdate?.();
			toastService.add('Включены пуш-уведомления', 'success');
		} catch (error: unknown) {
			console.error('Failed to subscribe:', error);
			toastService.add('Не удалось включить уведомления', 'error');
		} finally {
			isLoading = false;
		}
	}

	async function updateSettings(
		nextSettings: Partial<components['schemas']['UpdateUserSettingsInput']>,
		rollback: () => void
	) {
		isSavingSettings = true;
		const { error, response } = await client.PATCH('/me/settings', {
			body: nextSettings
		});

		if (error || !response.ok) {
			console.error('API Error:', error);
			toastService.add('Не удалось обновить настройки', 'error');
			rollback();
		} else {
			toastService.add('Настройки сохранены', 'success');
			onSettingsUpdate?.();
		}
		isSavingSettings = false;
	}

	function toggleReceiveAll() {
		void updateSettings(
			{
				receive_all_announcements: receiveAll
			},
			() => {
				receiveAll = user.settings.receive_all_announcements;
			}
		);
	}

	function toggleReceiveTelegram() {
		void updateSettings(
			{
				receive_telegram_notifications: receiveTelegram
			},
			() => {
				receiveTelegram = user.settings.receive_telegram_notifications;
			}
		);
	}

	async function sendTestNotification() {
		if (isSendingTest) {
			return;
		}

		try {
			isSendingTest = true;

			const { error, response } = await client.POST('/notifications/test');

			if (error || !response.ok) {
				console.error('API Error:', error);
				toastService.add('Не удалось отправить тест по каналам уведомлений', 'error');
				return;
			}

			toastService.add(
				'Тест отправлен. Если сайт открыт, проверь тост и колокольчик. Для системного пуш сверни или закрой приложение.',
				'success'
			);
		} catch (error) {
			console.error('Failed to send test notification:', error);
			toastService.add('Не удалось отправить тест по каналам уведомлений', 'error');
		} finally {
			isSendingTest = false;
		}
	}
</script>

<ProfileCardShell
	title="Уведомления"
	description="Выбери каналы, чтобы не пропустить расписание, анонсы и сервисные сообщения."
>
	{#snippet icon()}
		<BellOutline class="h-5 w-5" />
	{/snippet}

	<div class="rounded-lg border border-gray-200 dark:border-gray-700">
		<div class="flex items-start justify-between gap-3 p-3 sm:p-4">
			<div class="min-w-0">
				<span class="text-sm font-medium text-gray-900 dark:text-gray-300">
					Уведомления в браузере
				</span>
				<p class="mt-1 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
					Получать пуш-уведомления на этом устройстве.
				</p>
			</div>
			<Toggle
				checked={isSubscribed}
				disabled={isLoading}
				onclick={(e) => {
					e.preventDefault();
					toggleSubscription();
				}}
				color="green"
			/>
		</div>

		<div class="border-t border-gray-200 p-3 sm:p-4 dark:border-gray-700">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0">
					<span class="text-sm font-medium text-gray-900 dark:text-gray-300">Telegram</span>
					<p class="mt-1 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
						{#if hasTelegramAccount}
							Получать сообщения в Telegram-боте.
						{:else}
							Сначала подключи Telegram в блоке «Способы входа».
						{/if}
					</p>
				</div>
				<Toggle
					bind:checked={receiveTelegram}
					disabled={isSavingSettings || !hasTelegramAccount}
					onchange={toggleReceiveTelegram}
					color="green"
				/>
			</div>
		</div>

		<div class="border-t border-gray-200 p-3 sm:p-4 dark:border-gray-700">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0">
					<span class="text-sm font-medium text-gray-900 dark:text-gray-300">Все анонсы</span>
					<p class="mt-1 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
						Получать уведомления о начале каждого выступления.
					</p>
				</div>
				<Toggle
					bind:checked={receiveAll}
					disabled={isSavingSettings}
					onchange={toggleReceiveAll}
					color="green"
				/>
			</div>
		</div>
	</div>

	<div class="rounded-lg border border-gray-200 p-3 sm:p-4 dark:border-gray-700">
		<p class="mb-3 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
			Попробуй отправить себе пробное уведомление, чтобы убедиться, что всё работает. Важно:
			системные пуш-уведомления приходят только когда сайт закрыт.
		</p>
		<Button
			color="light"
			class="min-h-11 w-full sm:w-auto"
			disabled={isSendingTest}
			onclick={sendTestNotification}
		>
			{#if isSendingTest}
				Отправка…
			{:else}
				<BellSolid class="me-2 h-4 w-4" />
				Проверить уведомления
			{/if}
		</Button>
	</div>
</ProfileCardShell>

<Modal bind:open={showIosPwaModal} size="sm">
	{#snippet header()}
		<div class="flex items-center gap-2">
			<ArrowDownToBracketOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Установи приложение</h3>
		</div>
	{/snippet}

	<p class="text-sm text-gray-500 dark:text-gray-400">
		Пуш-уведомления на iOS доступны только в установленном приложении. Найди карточку «Установить
		приложение» на этой странице и следуй инструкции.
	</p>
	{#snippet footer()}
		<Button color="alternative" class="w-full" onclick={() => (showIosPwaModal = false)}
			>Понятно</Button
		>
	{/snippet}
</Modal>
