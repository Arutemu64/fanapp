<script lang="ts">
	import { createApiClient } from '$lib/api';
	import { Button, Modal, Toggle } from 'flowbite-svelte';
	import {
		AnnotationOutline,
		ArrowDownToBracketOutline,
		BellOutline,
		BellSolid
	} from 'flowbite-svelte-icons';
	const client = createApiClient();
	import type { components } from '$lib/api/schema';
	import type { CurrentUserDTO } from '$lib/types/user';

	import { PUBLIC_VAPID_KEY, PUBLIC_VK_GROUP_ID } from '$env/static/public';
	import { getPwaService } from '$lib/services/pwa.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { onMount } from 'svelte';

	import ProfileCardShell from './ProfileCardShell.svelte';

	interface Props {
		user: CurrentUserDTO;
		onSettingsUpdate?: () => void;
	}

	let { user, onSettingsUpdate }: Props = $props();

	let isSubscribed = $state(false);
	const toastService = getToastService();
	let isLoading = $state(true);
	// Writable $derived: the toggles bind to these and flip them optimistically,
	// then the rollback in updateSettings reassigns from `user.settings` on failure.
	// Because they derive from the prop, a successful refetch re-syncs them for free.
	let receiveAll = $derived(user.settings.receive_all_announcements);
	let receiveTelegram = $derived(user.settings.receive_telegram_notifications);
	let receiveVk = $derived(user.settings.receive_vk_notifications);
	let isSavingSettings = $state(false);
	let isSendingTest = $state(false);
	const pwa = getPwaService();
	let showIosPwaModal = $state(false);
	let showVkModal = $state(false);
	let hasTelegramAccount = $derived(
		user.social_identities.some((socialIdentity) => socialIdentity.provider === 'telegram')
	);
	let hasVkAccount = $derived(
		user.social_identities.some((socialIdentity) => socialIdentity.provider === 'vk')
	);
	// Link to the group's chat where the user grants "allow messages". Built from
	// the build-time group id, so it may be empty if VK notifications were not
	// configured for this deployment — the modal hides the button then.
	const vkGroupUrl = PUBLIC_VK_GROUP_ID ? `https://vk.ru/im?sel=-${PUBLIC_VK_GROUP_ID}` : null;

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

			// The browser has a local subscription; confirm the server still knows
			// about this exact endpoint, otherwise treat it as not subscribed so the
			// user can re-register (e.g. after the server lost the subscription).
			const { data } = await client.GET('/push/', {
				params: { query: { endpoint: subscription.endpoint } }
			});
			isSubscribed = data?.subscribed ?? false;
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

		if (pwa.isApplePlatform && !pwa.isInstalled) {
			showIosPwaModal = true;
			return;
		}

		isLoading = true;
		try {
			if (typeof Notification === 'undefined') {
				toastService.add('Твой браузер не поддерживает уведомления', 'error');
				return;
			}

			// PUBLIC_VAPID_KEY is baked in at build time, so it may be empty if push
			// notifications were not configured for this deployment.
			const vapidKey = PUBLIC_VAPID_KEY;
			if (!vapidKey) {
				toastService.add('Уведомления сейчас недоступны', 'error');
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
				applicationServerKey: urlBase64ToUint8Array(vapidKey)
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

	function toggleReceiveVk() {
		void updateSettings(
			{
				receive_vk_notifications: receiveVk
			},
			() => {
				receiveVk = user.settings.receive_vk_notifications;
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
				'Тест отправлен. Должны прийти тост, колокольчик и системное пуш-уведомление.',
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
	description="Настрой уведомления, чтобы не пропустить анонсы и важные сообщения."
>
	{#snippet icon()}
		<BellOutline class="h-5 w-5" />
	{/snippet}

	<div class="rounded-lg border border-gray-200 dark:border-gray-700">
		<div class="border-b border-gray-200 px-3 py-2.5 sm:px-4 dark:border-gray-700">
			<h4 class="text-sm font-semibold text-gray-900 dark:text-white">Каналы</h4>
		</div>

		<div class="flex items-start justify-between gap-3 p-3 sm:p-4">
			<div class="min-w-0">
				<span class="text-sm font-medium text-gray-900 dark:text-gray-300">Пуш-уведомления</span>
				<p class="mt-1 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
					Получать на этом устройстве.
				</p>
			</div>
			<Toggle
				checked={isSubscribed}
				aria-label="Включить пуш-уведомления на этом устройстве"
				disabled={isLoading}
				onclick={(e) => {
					e.preventDefault();
					void toggleSubscription();
				}}
				color="primary"
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
					aria-label="Получать уведомления в Telegram"
					disabled={isSavingSettings || !hasTelegramAccount}
					onchange={toggleReceiveTelegram}
					color="primary"
				/>
			</div>
		</div>

		<div class="border-t border-gray-200 p-3 sm:p-4 dark:border-gray-700">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0">
					<span class="text-sm font-medium text-gray-900 dark:text-gray-300">ВКонтакте</span>
					<p class="mt-1 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
						{#if hasVkAccount}
							Получать сообщения от сообщества во ВКонтакте.
						{:else}
							Сначала подключи ВКонтакте в блоке «Способы входа».
						{/if}
					</p>
					<button
						type="button"
						class="mt-1 text-sm font-medium text-primary-600 hover:underline dark:text-primary-400"
						onclick={() => (showVkModal = true)}
					>
						Как это работает?
					</button>
				</div>
				<Toggle
					bind:checked={receiveVk}
					aria-label="Получать уведомления во ВКонтакте"
					disabled={isSavingSettings || !hasVkAccount}
					onchange={toggleReceiveVk}
					color="primary"
				/>
			</div>
		</div>
	</div>

	<div class="rounded-lg border border-gray-200 dark:border-gray-700">
		<div class="border-b border-gray-200 px-3 py-2.5 sm:px-4 dark:border-gray-700">
			<h4 class="text-sm font-semibold text-gray-900 dark:text-white">Типы уведомлений</h4>
		</div>

		<div class="p-3 sm:p-4">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0">
					<span class="text-sm font-medium text-gray-900 dark:text-gray-300">Все анонсы</span>
					<p class="mt-1 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
						Получать уведомления о начале каждого выступления.
					</p>
				</div>
				<Toggle
					bind:checked={receiveAll}
					aria-label="Получать уведомления обо всех анонсах"
					disabled={isSavingSettings}
					onchange={toggleReceiveAll}
					color="primary"
				/>
			</div>
		</div>
	</div>

	<div class="rounded-lg border border-gray-200 p-3 sm:p-4 dark:border-gray-700">
		<p class="mb-3 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
			Попробуй отправить себе пробное уведомление, чтобы убедиться, что всё работает.
		</p>
		<Button
			color="alternative"
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

<Modal bind:open={showVkModal} size="sm">
	{#snippet header()}
		<div class="flex items-center gap-2">
			<AnnotationOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Уведомления во ВКонтакте</h3>
		</div>
	{/snippet}

	<p class="text-sm leading-relaxed text-gray-500 dark:text-gray-400">
		Чтобы получать уведомления во ВКонтакте, нужно разрешить сообществу писать тебе — без этого
		ВКонтакте не доставит сообщения.
	</p>
	<p class="mt-3 text-sm font-medium text-gray-900 dark:text-gray-300">Что сделать:</p>
	<ul
		class="mt-1 list-disc space-y-1 ps-5 text-sm leading-relaxed text-gray-500 dark:text-gray-400"
	>
		<li>Подключи аккаунт ВКонтакте в блоке «Способы входа».</li>
		<li>Открой сообщество и нажми «Разрешить сообщения».</li>
	</ul>
	{#snippet footer()}
		{#if vkGroupUrl}
			<Button color="primary" class="w-full" href={vkGroupUrl} target="_blank" rel="noopener">
				Открыть сообщество
			</Button>
		{/if}
		<Button color="alternative" class="w-full" onclick={() => (showVkModal = false)}>Понятно</Button
		>
	{/snippet}
</Modal>
