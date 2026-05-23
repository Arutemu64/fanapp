<script lang="ts">
	import { getToastService, ToastTypeColors } from '$lib/services/toasts.svelte';
	import { Toast, ToastContainer } from 'flowbite-svelte';
	import {
		CheckCircleSolid,
		CloseCircleSolid,
		ExclamationCircleSolid,
		BellSolid
	} from 'flowbite-svelte-icons';
	import { fly } from 'svelte/transition';
	import { formatRelativeTime } from '$lib/utils/formatters';

	const toastService = getToastService();

	function handleTouchStart(e: TouchEvent) {
		const target = e.currentTarget as HTMLElement;
		target.dataset.startX = e.changedTouches[0].screenX.toString();
		target.style.transition = 'none';
	}

	function handleTouchMove(e: TouchEvent) {
		const target = e.currentTarget as HTMLElement;
		const startX = parseFloat(target.dataset.startX || '0');
		if (!startX) return;

		const currentX = e.changedTouches[0].screenX;
		const deltaX = currentX - startX;

		target.style.transform = `translateX(${deltaX}px)`;
		target.style.opacity = Math.max(0, 1 - Math.abs(deltaX) / 200).toString();
	}

	function handleTouchEnd(e: TouchEvent, id: number) {
		const target = e.currentTarget as HTMLElement;
		const startX = parseFloat(target.dataset.startX || '0');
		const currentX = e.changedTouches[0].screenX;
		const deltaX = currentX - startX;

		target.style.transition = 'transform 0.2s ease-out, opacity 0.2s ease-out';

		if (Math.abs(deltaX) > 50) {
			target.style.transform = `translateX(${deltaX > 0 ? 100 : -100}%)`;
			target.style.opacity = '0';
			setTimeout(() => {
				toastService.dismiss(id);
			}, 200);
		} else {
			target.style.transform = 'translateX(0)';
			target.style.opacity = '1';
		}
		
		delete target.dataset.startX;
	}
</script>

<ToastContainer
	class="pointer-events-none !sticky !top-4 !right-auto !bottom-auto !left-auto z-50 mx-auto flex h-0 w-full max-w-7xl flex-col overflow-visible px-4 md:px-6 lg:px-8"
>
	{#each toastService.items as toast (toast.id)}
		<!-- Keep the toast stack inside the page container so it never covers the top navbar. -->
		<div
			role={toast.type === 'error' ? 'alert' : 'status'}
			aria-live={toast.type === 'error' ? 'assertive' : 'polite'}
			aria-atomic="true"
			class="pointer-events-auto w-full sm:ml-auto sm:max-w-sm"
			transition:fly={{ y: -16, duration: 300 }}
			ontouchstart={handleTouchStart}
			ontouchmove={handleTouchMove}
			ontouchend={(e) => handleTouchEnd(e, toast.id)}
		>
			{#if toast.type === 'push' && toast.notification}
				<Toast
					align={false}
					color={undefined}
					dismissable={true}
					onclose={() => toastService.dismiss(toast.id)}
					class="w-full max-w-sm rounded-lg bg-white p-4 text-gray-500 shadow dark:bg-gray-800 dark:text-gray-400"
				>
					<span class="font-semibold text-gray-900 dark:text-white">Новое уведомление</span>
					<div class="mt-3 flex items-start">
						<div
							class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400"
						>
							<BellSolid class="h-5 w-5" />
						</div>
						<div class="ms-3 min-w-0 flex-1">
							<h4 class="text-sm font-semibold text-gray-900 dark:text-white">
								{toast.notification.title}
							</h4>
							{#if toast.notification.body}
								<div class="mt-1 line-clamp-2 text-sm font-normal text-gray-500 dark:text-gray-400">
									{toast.notification.body}
								</div>
							{/if}
							<span class="mt-1 block text-xs font-medium text-primary-600 dark:text-primary-500"
								>{formatRelativeTime(toast.notification.created_at)}</span
							>
						</div>
					</div>
				</Toast>
			{:else}
				<Toast
					color={toast.type === 'push' ? undefined : ToastTypeColors[toast.type]}
					dismissable={true}
					class="w-full max-w-sm"
					onclose={() => toastService.dismiss(toast.id)}
				>
					{#snippet icon()}
						{#if toast.type == 'success'}
							<CheckCircleSolid class="h-5 w-5" />
						{:else if toast.type == 'info'}
							<ExclamationCircleSolid class="h-5 w-5" />
						{:else if toast.type == 'warning'}
							<ExclamationCircleSolid class="h-5 w-5" />
						{:else if toast.type == 'error'}
							<CloseCircleSolid class="h-5 w-5" />
						{/if}
					{/snippet}
					{toast.message}
				</Toast>
			{/if}
		</div>
	{/each}
</ToastContainer>
