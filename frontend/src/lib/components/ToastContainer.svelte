<script lang="ts">
	import type { Pathname } from '$app/types';
	import type { PushToastItem, StatusToastItem } from '$lib/services/toasts.svelte';
	import type { NotificationDTO } from '$lib/types/notifications';

	import { resolve } from '$app/paths';
	import { getToastService, StatusToastColors } from '$lib/services/toasts.svelte';
	import { formatRelativeTime } from '$lib/utils/formatters';
	import { Toast, ToastContainer } from 'flowbite-svelte';
	import {
		BellSolid,
		CheckCircleSolid,
		CloseCircleSolid,
		ExclamationCircleSolid
	} from 'flowbite-svelte-icons';
	import { prefersReducedMotion } from 'svelte/motion';
	import { fly } from 'svelte/transition';

	const toastService = getToastService();

	// Toasts enter from the edge they are anchored to: push toasts drop down from
	// the top, status toasts rise up from the bottom. When the user prefers reduced
	// motion, drop the slide distance and duration so they simply appear/disappear.
	let pushFly = $derived(
		prefersReducedMotion.current ? { y: 0, duration: 0 } : { y: -16, duration: 300 }
	);
	let statusFly = $derived(
		prefersReducedMotion.current ? { y: 0, duration: 0 } : { y: 16, duration: 300 }
	);

	function handleTouchStart(e: TouchEvent) {
		const target = e.currentTarget as HTMLElement;
		const touch = e.changedTouches?.[0];
		if (!touch) return;
		target.dataset.startX = touch.screenX.toString();
		target.style.transition = 'none';
	}

	function handleTouchMove(e: TouchEvent) {
		const target = e.currentTarget as HTMLElement;
		const startX = parseFloat(target.dataset.startX || '0');
		if (!startX) return;

		const touch = e.changedTouches?.[0];
		if (!touch) return;
		const currentX = touch.screenX;
		const deltaX = currentX - startX;

		target.style.transform = `translateX(${deltaX}px)`;
		target.style.opacity = Math.max(0, 1 - Math.abs(deltaX) / 200).toString();
	}

	function handleTouchEnd(e: TouchEvent, id: number) {
		const target = e.currentTarget as HTMLElement;
		const startX = parseFloat(target.dataset.startX || '0');
		const touch = e.changedTouches?.[0];
		if (!touch) return;
		const currentX = touch.screenX;
		const deltaX = currentX - startX;

		// Honour reduced motion: snap back / dismiss instantly instead of easing.
		const settleMs = prefersReducedMotion.current ? 0 : 200;
		target.style.transition = settleMs ? 'transform 0.2s ease-out, opacity 0.2s ease-out' : 'none';

		if (Math.abs(deltaX) > 50) {
			target.style.transform = `translateX(${deltaX > 0 ? 100 : -100}%)`;
			target.style.opacity = '0';
			setTimeout(() => {
				toastService.dismiss(id);
			}, settleMs);
		} else {
			target.style.transform = 'translateX(0)';
			target.style.opacity = '1';
		}

		delete target.dataset.startX;
	}
</script>

{#snippet pushContent(notification: NotificationDTO)}
	<div
		class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400"
	>
		<BellSolid class="h-5 w-5" />
	</div>
	<div class="ms-3 min-w-0 flex-1">
		<h4 class="text-sm font-semibold text-gray-900 dark:text-white">
			{notification.title}
		</h4>
		{#if notification.body}
			<!-- Body is sanitized to a safe HTML subset on the backend (HtmlSanitizer). -->
			<div class="mt-1 line-clamp-2 text-sm font-normal text-gray-500 dark:text-gray-400">
				<!-- eslint-disable-next-line svelte/no-at-html-tags -->
				{@html notification.body}
			</div>
		{/if}
		<span class="mt-1 block text-xs font-medium text-primary-600 dark:text-primary-400"
			>{formatRelativeTime(notification.created_at)}</span
		>
	</div>
{/snippet}

{#snippet statusBody(toast: StatusToastItem)}
	<Toast
		color={StatusToastColors[toast.type]}
		dismissable={true}
		class="w-full max-w-sm"
		onclose={() => toastService.dismiss(toast.id)}
	>
		{#snippet icon()}
			{#if toast.type === 'success'}
				<CheckCircleSolid class="h-5 w-5" />
			{:else if toast.type === 'error'}
				<CloseCircleSolid class="h-5 w-5" />
			{:else}
				<ExclamationCircleSolid class="h-5 w-5" />
			{/if}
		{/snippet}
		{toast.message}
	</Toast>
{/snippet}

{#snippet pushBody(toast: PushToastItem)}
	<Toast
		align={false}
		color={undefined}
		dismissable={true}
		onclose={() => toastService.dismiss(toast.id)}
		class="w-full max-w-sm rounded-lg bg-white p-4 text-gray-500 shadow dark:bg-gray-800 dark:text-gray-400"
	>
		<span class="font-semibold text-gray-900 dark:text-white">Новое уведомление</span>
		{#if toast.notification.path}
			<!-- Whole body deep-links to the notification's in-app target on tap. -->
			<a
				href={resolve(toast.notification.path as Pathname)}
				class="mt-3 flex items-start"
				onclick={() => toastService.dismiss(toast.id)}
			>
				{@render pushContent(toast.notification)}
			</a>
		{:else}
			<div class="mt-3 flex items-start">
				{@render pushContent(toast.notification)}
			</div>
		{/if}
	</Toast>
{/snippet}

<!-- Push notifications: inbound events, pinned to the top like OS notifications.
     Sticky inside the page container so the stack never covers the top navbar. -->
<ToastContainer
	class="pointer-events-none !sticky !top-4 !right-auto !bottom-auto !left-auto z-50 mx-auto flex h-0 w-full max-w-7xl flex-col overflow-visible px-4 md:px-6 lg:px-8"
>
	{#each toastService.pushItems as toast (toast.id)}
		<div
			role="status"
			aria-live="polite"
			aria-atomic="true"
			class="pointer-events-auto w-full sm:ml-auto sm:max-w-sm"
			transition:fly={pushFly}
			ontouchstart={handleTouchStart}
			ontouchmove={handleTouchMove}
			ontouchend={(e) => handleTouchEnd(e, toast.id)}
		>
			{@render pushBody(toast)}
		</div>
	{/each}
</ToastContainer>

<!-- Action feedback: bottom-center on mobile (raised above the fixed bottom nav,
     h-16 + safe-area), bottom-right on desktop where that nav is hidden.
     flex-col-reverse so the newest toast sits at the bottom, nearest its edge. -->
<ToastContainer
	class="pointer-events-none !fixed !top-auto !right-auto !bottom-[calc(4.5rem+env(safe-area-inset-bottom))] !left-auto z-50 mx-auto flex w-full max-w-7xl flex-col-reverse px-4 md:!bottom-4 md:px-6 lg:px-8"
>
	{#each toastService.statusItems as toast (toast.id)}
		<div
			role={toast.type === 'error' ? 'alert' : 'status'}
			aria-live={toast.type === 'error' ? 'assertive' : 'polite'}
			aria-atomic="true"
			class="pointer-events-auto w-full sm:mx-auto sm:max-w-sm"
			transition:fly={statusFly}
			ontouchstart={handleTouchStart}
			ontouchmove={handleTouchMove}
			ontouchend={(e) => handleTouchEnd(e, toast.id)}
		>
			{@render statusBody(toast)}
		</div>
	{/each}
</ToastContainer>
