<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { Button } from '$lib/components/ui/button';
	import * as Card from '$lib/components/ui/card';
	import { statusTitle } from '$lib/utils/errorTitle';
	import { AlertCircle, ArrowLeft, Home, Lock, RotateCw } from '@lucide/svelte';

	type Variant = 'fullscreen' | 'inline';

	// `fullscreen` takes over the whole viewport (root errors: 404, auth, root load
	// failures). `inline` fills the content area only, so the app shell — navbar,
	// sidebar, bottom nav — stays visible and navigable around it.
	// `error` is the boundary's own error, which +error.svelte receives for a
	// rendering error. Prefer it to `page.error`: every failing boundary — the
	// navbar's bell included — writes its error there, so a later failure
	// elsewhere could replace this page's message and «Код ошибки».
	let { variant = 'fullscreen', error }: { variant?: Variant; error?: App.Error } = $props();

	let shownError = $derived(error ?? page.error);
	let status = $derived(page.status);
	let errorMessage = $derived(shownError?.message);
	let errorId = $derived(shownError?.errorId);

	// A navigation normally replaces the error page. One that survives a
	// navigation to another URL was rendered by a failed rendering-error
	// boundary, which SvelteKit 2 never resets, so it would stay mounted over
	// the destination (sveltejs/kit#15694). Reload onto the destination instead.
	// Compared by URL, not by skipping the first call: afterNavigate also fires
	// for the navigation that mounted this page, but a rendering error mounts
	// after that navigation settles, so "first call" is timing-dependent.
	// TODO: delete on SvelteKit 3 — fixed in @sveltejs/kit 3.0.0-next.8 (#16296),
	// not backported to 2.x.
	const renderedAt = page.url.href;
	afterNavigate(({ to }) => {
		if (to && to.url.href !== renderedAt) {
			window.location.reload();
		}
	});

	let title = $derived(statusTitle(status));

	// A genuine 403 gets the lock icon; everything else gets the generic alert icon.
	let StatusIcon = $derived(status === 403 ? Lock : AlertCircle);

	let description = $derived.by(() => {
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
			<div
				class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-destructive/15 text-destructive"
			>
				<StatusIcon class="h-8 w-8" />
			</div>

			<span class="mb-1 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
				Ошибка {status}
			</span>

			<h2 class="mb-2 text-xl font-bold text-foreground sm:text-2xl">
				{title}
			</h2>

			<p class="mb-6 text-sm text-muted-foreground">
				{description}
			</p>

			{#if errorId}
				<!-- Something a user can quote in feedback; matches the error_id tag on the
				     GlitchTip event (see handleError in hooks.client.ts). -->
				<p class="-mt-4 mb-6 text-xs text-muted-foreground">
					Код ошибки: <span class="font-mono select-all">{errorId}</span>
				</p>
			{/if}

			<div class="flex w-full flex-col gap-2">
				{#if status >= 500}
					<Button class="w-full" onclick={handleRetry}>
						<RotateCw data-icon="inline-start" />
						Попробовать снова
					</Button>
				{/if}

				<Button href="/" variant={status >= 500 ? 'outline' : 'default'} class="w-full">
					<Home data-icon="inline-start" />
					На главную
				</Button>

				<Button type="button" variant="ghost" class="w-full" onclick={handleGoBack}>
					<ArrowLeft data-icon="inline-start" />
					Вернуться назад
				</Button>
			</div>
		</div>
	</Card.Root>
</div>
