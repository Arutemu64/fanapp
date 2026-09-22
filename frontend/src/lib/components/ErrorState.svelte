<script lang="ts">
	import { page } from '$app/state';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { online } from '$lib/services/online.svelte';
	import { statusTitle } from '$lib/utils/errorTitle';
	import { AlertCircle, ArrowLeft, Home, Lock, RotateCw } from '@lucide/svelte';

	type Variant = 'fullscreen' | 'inline';

	// `fullscreen` takes over the whole viewport (root errors: 404, auth, root load
	// failures). `inline` fills the content area only, so the app shell — navbar,
	// sidebar, bottom nav — stays visible and navigable around it.
	let { variant = 'fullscreen' }: { variant?: Variant } = $props();

	let status = $derived(page.status);
	let errorMessage = $derived(page.error?.message);

	// Most load failures while offline surface here as a 500/503. Detect the real
	// cause and show a calm connectivity page instead of a scary server-error
	// screen. Read the shared online state directly so this works without the
	// OfflineService context too.
	// A genuine 403/404 is a real server answer — never reframe it as offline.
	let offline = $derived(!online.current && status !== 403 && status !== 404);

	let title = $derived(offline ? 'Нет интернета' : statusTitle(status));

	// A genuine 403 gets the lock icon; everything else (including offline, which
	// is never a 403) gets the generic alert icon. Offline is the only yellow
	// state; all others are red.
	let StatusIcon = $derived(status === 403 ? Lock : AlertCircle);
	let iconColorClass = $derived(
		offline ? 'bg-warning/15 text-warning' : 'bg-destructive/15 text-destructive'
	);

	let description = $derived.by(() => {
		if (offline) return 'Проверь подключение к сети. Часть данных доступна офлайн.';
		if (errorMessage) return errorMessage;
		if (status === 403) return 'У тебя нет прав для просмотра этой страницы.';
		if (status === 404) return 'Похоже, эта страница не существует, была удалена или перенесена.';
		return 'Произошла непредвиденная ошибка на сервере или отсутствует интернет-соединение.';
	});

	// Fullscreen owns the viewport background; inline inherits the shell's surface.
	let wrapperClass = $derived(
		variant === 'fullscreen'
			? 'flex min-h-dvh items-center justify-center bg-background px-4 py-6 sm:py-10'
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
	<Card.Root class="w-full max-w-md rounded-2xl p-6 text-center sm:p-8">
		<div class="flex flex-col items-center justify-center">
			<div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full {iconColorClass}">
				<StatusIcon class="h-8 w-8" />
			</div>

			<span class="mb-1 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
				{offline ? 'Офлайн' : `Ошибка ${status}`}
			</span>

			<h2 class="mb-2 text-xl font-bold text-foreground sm:text-2xl">
				{title}
			</h2>

			<p class="mb-6 text-sm text-muted-foreground">
				{description}
			</p>

			<div class="flex w-full flex-col gap-2">
				{#if offline || status >= 500}
					<Button class="min-h-11 w-full font-medium" onclick={handleRetry}>
						<RotateCw data-icon="inline-start" />
						Попробовать снова
					</Button>
				{/if}

				<Button
					href="/"
					variant={offline || status >= 500 ? 'outline' : 'default'}
					class="min-h-11 w-full font-medium"
				>
					<Home data-icon="inline-start" />
					На главную
				</Button>

				<Button
					type="button"
					variant="ghost"
					class="min-h-11 w-full font-medium"
					onclick={handleGoBack}
				>
					<ArrowLeft data-icon="inline-start" />
					Вернуться назад
				</Button>
			</div>
		</div>
	</Card.Root>
</div>
