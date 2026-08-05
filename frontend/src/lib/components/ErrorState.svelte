<script lang="ts">
	import { page } from '$app/state';
	import { reachability } from '$lib/services/reachability';
	import { statusTitle } from '$lib/utils/errorTitle';
	import { Button, Card } from 'flowbite-svelte';
	import {
		ArrowLeftOutline,
		ExclamationCircleSolid,
		HomeOutline,
		LockSolid,
		RefreshOutline
	} from 'flowbite-svelte-icons';

	type Variant = 'fullscreen' | 'inline';

	// `fullscreen` takes over the whole viewport (root errors: 404, auth, root load
	// failures). `inline` fills the content area only, so the app shell — navbar,
	// sidebar, bottom nav — stays visible and navigable around it.
	let { variant = 'fullscreen' }: { variant?: Variant } = $props();

	let status = $derived(page.status);
	let errorMessage = $derived(page.error?.message);

	// Most load failures while offline surface here as a 500/503. Detect the real
	// cause (backend unreachable) and show a calm "you're offline" page instead of
	// a scary server-error screen. Read straight from the reachability module so
	// this works without the OfflineService context too.
	let online = $derived(reachability.current);
	// A genuine 403/404 is a real server answer — never reframe it as offline.
	let offline = $derived(!online && status !== 403 && status !== 404);

	let title = $derived(offline ? 'Нет соединения' : statusTitle(status));

	// A genuine 403 gets the lock icon; everything else (including offline, which
	// is never a 403) gets the generic alert icon. Offline is the only yellow
	// state; all others are red.
	let StatusIcon = $derived(status === 403 ? LockSolid : ExclamationCircleSolid);
	let iconColorClass = $derived(
		offline
			? 'bg-yellow-100 text-yellow-500 dark:bg-yellow-900/30 dark:text-yellow-400'
			: 'bg-red-100 text-red-500 dark:bg-red-900/30 dark:text-red-400'
	);

	let description = $derived.by(() => {
		if (offline) return 'Проверь соединение и попробуй снова. Часть данных доступна офлайн.';
		if (errorMessage) return errorMessage;
		if (status === 403) return 'У тебя нет прав для просмотра этой страницы.';
		if (status === 404) return 'Похоже, эта страница не существует, была удалена или перенесена.';
		return 'Произошла непредвиденная ошибка на сервере или отсутствует интернет-соединение.';
	});

	// Fullscreen owns the viewport background; inline inherits the shell's surface.
	let wrapperClass = $derived(
		variant === 'fullscreen'
			? 'flex min-h-dvh items-center justify-center bg-gray-50 px-4 py-6 sm:py-10 dark:bg-gray-950'
			: 'flex min-h-[60dvh] items-center justify-center px-4 py-6'
	);

	function handleGoBack() {
		window.history.back();
	}

	function handleRetry() {
		window.location.reload();
	}
</script>

<div class={wrapperClass}>
	<Card class="w-full max-w-md rounded-2xl p-6 text-center sm:p-8">
		<div class="flex flex-col items-center justify-center">
			<div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full {iconColorClass}">
				<StatusIcon class="h-8 w-8" />
			</div>

			<span
				class="mb-1 text-xs font-semibold tracking-wider text-gray-400 uppercase dark:text-gray-500"
			>
				{offline ? 'Офлайн' : `Ошибка ${status}`}
			</span>

			<h2 class="mb-2 text-xl font-bold text-gray-900 sm:text-2xl dark:text-white">
				{title}
			</h2>

			<p class="mb-6 text-sm text-gray-500 dark:text-gray-400">
				{description}
			</p>

			<div class="flex w-full flex-col gap-2">
				{#if offline || status >= 500}
					<Button
						color="primary"
						class="min-h-11 w-full rounded-xl font-medium"
						onclick={handleRetry}
					>
						<RefreshOutline class="me-2 h-4 w-4" />
						Попробовать снова
					</Button>
				{/if}

				<Button
					href="/"
					color={offline || status >= 500 ? 'alternative' : 'primary'}
					class="min-h-11 w-full rounded-xl font-medium"
				>
					<HomeOutline class="me-2 h-4 w-4" />
					На главную
				</Button>

				<Button
					type="button"
					color="light"
					class="min-h-11 w-full rounded-xl font-medium"
					onclick={handleGoBack}
				>
					<ArrowLeftOutline class="me-2 h-4 w-4" />
					Вернуться назад
				</Button>
			</div>
		</div>
	</Card>
</div>
