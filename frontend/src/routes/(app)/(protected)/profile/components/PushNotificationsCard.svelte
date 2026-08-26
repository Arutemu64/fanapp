<script lang="ts">
	import { createApiClient } from '$lib/api';
	import { Button, Toggle } from 'flowbite-svelte';
	import { BellOutline, BellSolid } from 'flowbite-svelte-icons';
	const client = createApiClient();
	import type { components } from '$lib/api/schema';
	import type { CurrentUserDTO } from '$lib/types/user';

	import { PUBLIC_VAPID_KEY, PUBLIC_VK_GROUP_ID } from '$env/static/public';
	import { getPwaService } from '$lib/services/pwa.svelte';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { onMount } from 'svelte';

	import IosPwaModal from './IosPwaModal.svelte';
	import ProfileCardShell from './ProfileCardShell.svelte';
	import { urlBase64ToUint8Array } from './push';
	import VkNotificationsModal from './VkNotificationsModal.svelte';

	interface Props {
		user: CurrentUserDTO;
		onSettingsUpdate?: () => void;
	}

	let { user, onSettingsUpdate }: Props = $props();

	let isSubscribed = $state(false);
	// Once the browser permission is "denied" it never prompts again, so the
	// toggle is a dead end — surface a persistent hint on how to unblock instead.
	let notificationsBlocked = $state(false);
	// In-app browsers (Telegram, VK, Instagram, …) run a WebView without Service
	// Worker / Push support, so push can never work there — and on Android they
	// report a plain Chrome UA, so we detect the missing capability rather than
	// sniffing the user agent. Surfaces a hint to open the app in a real browser
	// instead of letting the toggle fail with a generic error.
	let pushUnsupported = $state(false);
	const toastService = getToastService();
	let isLoading = $state(true);
	let hasVkAccount = $derived(
		user.social_identities.some((socialIdentity) => socialIdentity.provider === 'vk')
	);
	// Writable $derived: the toggles bind to these and flip them optimistically,
	// then the rollback in updateSettings reassigns from `user.settings` on failure.
	// Because they derive from the prop, a successful refetch re-syncs them for free.
	let receiveAll = $derived(user.settings.receive_all_announcements);
	// The backend won't deliver VK messages until a VK identity is linked, so the
	// stored flag is inert while unlinked. Reflect the effective state — off until
	// VK is connected — rather than the raw setting, which would read "on" next to
	// the "connect VK first" hint. Only interactive once linked (Toggle is disabled
	// otherwise), so the optimistic flip and rollback still see the raw value.
	let receiveVk = $derived(hasVkAccount && user.settings.receive_vk_notifications);
	let isSavingSettings = $state(false);
	let isSendingTest = $state(false);
	const pwa = getPwaService();
	let showIosPwaModal = $state(false);
	let showVkModal = $state(false);
	// Link to the group's chat where the user grants "allow messages". Built from
	// the build-time group id, so it may be empty if VK notifications were not
	// configured for this deployment — the modal hides the button then.
	const vkGroupUrl = PUBLIC_VK_GROUP_ID ? `https://vk.ru/im?sel=-${PUBLIC_VK_GROUP_ID}` : null;

	async function checkSubscription() {
		try {
			notificationsBlocked =
				typeof Notification !== 'undefined' && Notification.permission === 'denied';
			if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
				pushUnsupported = true;
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
					notificationsBlocked = permission === 'denied';
					toastService.add('Уведомления не разрешены', 'error');
					return;
				}
			} else if (Notification.permission === 'denied') {
				notificationsBlocked = true;
				toastService.add('Уведомления заблокированы в браузере', 'error');
				return;
			}

			notificationsBlocked = false;

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
				toastService.add('Не удалось подключить устройство. Попробуй ещё раз', 'error');
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
				toastService.add('Не удалось включить уведомления. Попробуй ещё раз', 'error');
				await subscription.unsubscribe();
				return;
			}

			isSubscribed = true;
			onSettingsUpdate?.();
			toastService.add('Пуш-уведомления включены', 'success');
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
				toastService.add('Не удалось отправить тестовое уведомление', 'error');
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
				<span class="text-sm font-medium text-gray-900 dark:text-gray-300">На этом устройстве</span>
				<p class="mt-1 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
					Приходят как обычные уведомления телефона, даже когда приложение закрыто.
				</p>
				{#if pushUnsupported}
					<p class="mt-2 text-sm leading-relaxed text-gray-500 dark:text-gray-400">
						Чтобы получать уведомления, открой приложение в браузере — Chrome или Safari. Во
						встроенном браузере они не работают.
					</p>
				{:else if notificationsBlocked}
					<p class="mt-2 text-sm leading-relaxed text-red-600 dark:text-red-400">
						Уведомления заблокированы в браузере. Открой настройки сайта (значок замка рядом с
						адресом) и разреши уведомления.
					</p>
				{/if}
			</div>
			<Toggle
				checked={isSubscribed}
				aria-label="Включить уведомления на этом устройстве"
				disabled={isLoading || pushUnsupported}
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

<IosPwaModal bind:open={showIosPwaModal} />

<VkNotificationsModal bind:open={showVkModal} {vkGroupUrl} />
