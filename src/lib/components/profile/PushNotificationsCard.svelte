<script lang="ts">
	import { Card, Button, Toggle } from 'flowbite-svelte';
	import { BellOutline } from 'flowbite-svelte-icons';
	import { client } from '$lib/api';
	import { getToastService } from '$lib/stores/toasts.svelte';
	import { PUBLIC_VAPID_KEY } from '$env/static/public';
	import { onMount } from 'svelte';

	let isSubscribed = $state(false);
	const toastService = getToastService();
	let isLoading = $state(true);

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
			isSubscribed = !!subscription;
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
			// we don't have an API to unsubscribe, but we could unsubscribe locally
			// In fact, it might be better to just let users disable notifications via browser settings
			// But let's unsubscribe locally for now
			try {
				isLoading = true;
				const registration = await navigator.serviceWorker.ready;
				const subscription = await registration.pushManager.getSubscription();
				if (subscription) {
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

		isLoading = true;
		try {
			if (Notification.permission === 'denied') {
				toastService.add('Уведомления заблокированы в настройках браузера', 'error');
				isLoading = false;
				return;
			}

			const registration = await navigator.serviceWorker.register('/service-worker.js', {
				type: import.meta.env.DEV ? 'module' : 'classic'
			});

			// Wait until service worker is active
			await navigator.serviceWorker.ready;

			const subscription = await registration.pushManager.subscribe({
				userVisibleOnly: true,
				applicationServerKey: urlBase64ToUint8Array(PUBLIC_VAPID_KEY)
			});

			// Send to backend
			const subJson = subscription.toJSON();

			const { error } = await client.POST('/notifications/subscribe', {
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
			<span class="text-sm font-medium text-gray-900 dark:text-gray-300"> Push-уведомления </span>
			<Toggle
				checked={isSubscribed}
				disabled={isLoading}
				onchange={toggleSubscription}
				color="green"
			/>
		</div>
	</div>
</Card>
