<script lang="ts">
	import { Card, Button, Toggle, Modal } from 'flowbite-svelte';
	import { BellOutline, ShareNodesOutline } from 'flowbite-svelte-icons';
	import { client } from '$lib/api';
	import { getPwaService } from '$lib/stores/pwa.svelte';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import { PUBLIC_VAPID_KEY } from '$env/static/public';
	import { onMount } from 'svelte';
	import type { CurrentUserDTO } from '$lib/types/user';
	import type { components } from '$lib/api/v1';

	let {
		user,
		pushSubscriptions = []
	}: {
		user: CurrentUserDTO;
		pushSubscriptions?: components['schemas']['PushSubscriptionDTO'][];
	} = $props();

	let isSubscribed = $state(false);
	const toastService = getToastService();
	let isLoading = $state(true);
	let receiveAll = $state(user.settings.receive_all_announcements);
	let isSavingSettings = $state(false);
	const pwa = getPwaService();
	let showIosPwaModal = $state(false);

	// Convert base64 VAPID key to Uint8Array required by pushManager
	function urlBase64ToUint8Array(base64String: string) {
		const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
		const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');

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

			// Check if the current subscription exists on the server
			const serverSub = pushSubscriptions.find((s) => s.endpoint === subscription.endpoint);

			if (serverSub) {
				isSubscribed = true;
			} else {
				// We have a local subscription but it's not on the server
				// We consider this "not subscribed" for the UI toggle
				isSubscribed = false;
			}
		} catch (error) {
			console.error('Error checking push subscription:', error);
		} finally {
			isLoading = false;
		}
	}

	onMount(() => {
		checkSubscription();
	});

	async function toggleSubscription() {
		if (isSubscribed) {
			try {
				isLoading = true;
				const registration = await navigator.serviceWorker.ready;
				const subscription = await registration.pushManager.getSubscription();
				if (subscription) {
					// Send delete request to backend
					const { error } = await client.DELETE('/push', {
						body: {
							endpoint: subscription.endpoint
						}
					});

					if (error) {
						console.error('Failed to remove subscription from server:', error);
						// We proceed with local unsubscription anyway to keep UI in sync
					}

					await subscription.unsubscribe();
					isSubscribed = false;
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

		// Subscription logic
		if (pwa.isIOS && !pwa.isInstalled) {
			showIosPwaModal = true;
			return;
		}

		isLoading = true;
		try {
			if (typeof Notification === 'undefined') {
				toastService.add('Ваш браузер не поддерживает уведомления', 'error');
				return;
			}

			// Permission request is required if not granted
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

			// Use the existing SvelteKit-registered service worker
			const registration = await navigator.serviceWorker.ready;

			const subscription = await registration.pushManager.subscribe({
				userVisibleOnly: true,
				applicationServerKey: urlBase64ToUint8Array(PUBLIC_VAPID_KEY)
			});

			// Send to backend
			const subJson = subscription.toJSON();

			const { error } = await client.POST('/push', {
				body: {
					endpoint: subJson.endpoint!,
					p256dh: subJson.keys?.p256dh!,
					auth: subJson.keys?.auth!
				}
			});

			if (error) {
				console.error('API Error:', error);
				toastService.add('Ошибка при подписке на уведомления', 'error');
				// revert local subscription if backend fails
				await subscription.unsubscribe();
				return;
			}

			isSubscribed = true;
			toastService.add('Включены Push-уведомления', 'success');
		} catch (e: any) {
			console.error('Failed to subscribe:', e);
			toastService.add('Не удалось включить уведомления', 'error');
		} finally {
			isLoading = false;
		}
	}

	async function toggleReceiveAll() {
		isSavingSettings = true;
		const { error } = await client.PATCH('/users/me/settings', {
			body: {
				receive_all_announcements: receiveAll
			}
		});

		if (error) {
			console.error('API Error:', error);
			toastService.add('Не удалось обновить настройки', 'error');
			// Revert the local state since backend failed
			receiveAll = !receiveAll;
		} else {
			toastService.add('Настройки сохранены', 'success');
		}
		isSavingSettings = false;
	}
</script>

<Card class="w-full max-w-none rounded-lg bg-white shadow dark:bg-gray-800">
	<div class="p-6">
		<div class="mb-4 flex items-center gap-2">
			<BellOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			<h3 class="text-lg font-bold text-gray-900 dark:text-white">Уведомления</h3>
		</div>

		<p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
			Получайте важные уведомления. Включите, чтобы не пропустить расписание и анонсы.
		</p>

		<div class="flex items-center justify-between">
			<span class="text-sm font-medium text-gray-900 dark:text-gray-300"
				>Уведомления в браузере</span
			>
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

		<div
			class="mt-4 flex items-center justify-between border-t border-gray-200 pt-4 dark:border-gray-700"
		>
			<div>
				<span class="text-sm font-medium text-gray-900 dark:text-gray-300"> Все анонсы </span>
				<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
					Получать уведомления о начале каждого выступления
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
</Card>

<Modal title="Установите приложение" bind:open={showIosPwaModal} autoclose size="sm">
	<div class="space-y-4">
		<p class="text-base leading-relaxed text-gray-500 dark:text-gray-400">
			Для работы Push-уведомлений на iOS необходимо добавить приложение на экран «Домой».
		</p>
		<div
			class="flex items-center gap-3 rounded-lg bg-gray-50 p-4 text-sm text-gray-700 dark:bg-gray-700 dark:text-gray-300"
		>
			<div class="flex flex-col gap-2">
				<div class="flex items-center gap-2">
					<span
						class="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary-600 dark:bg-primary-900 dark:text-primary-300"
						>1</span
					>
					<span>Нажмите кнопку <strong>«Поделиться»</strong> в браузере</span>
					<ShareNodesOutline class="h-5 w-5 text-gray-500" />
				</div>
				<div class="flex items-center gap-2 text-primary-600"></div>
				<div class="flex items-center gap-2">
					<span
						class="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary-600 dark:bg-primary-900 dark:text-primary-300"
						>2</span
					>
					<span>Выберите <strong>«На экран „Домой“»</strong></span>
				</div>
			</div>
		</div>
	</div>
	{#snippet footer()}
		<Button color="alternative" class="w-full">Понятно</Button>
	{/snippet}
</Modal>
