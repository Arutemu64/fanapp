<script lang="ts">
	import { updated } from '$app/state';
	import { Button } from '$lib/components/ui/button';
	import { RotateCw } from '@lucide/svelte';

	// SvelteKit polls `_app/version.json` (`kit.version.pollInterval` in
	// svelte.config.js) and flips `updated.current` once a deploy lands. We never
	// reload mid-session on our own — that could drop a half-filled form — so the
	// user chooses when.
	// https://svelte.dev/docs/kit/$app-state#updated

	// The poll alone can leave an installed PWA, reopened after hours in the
	// background, on the old build until the next tick; re-check on foreground.
	function checkForUpdate() {
		if (document.visibilityState !== 'visible') return;
		void updated.check();
	}

	function applyUpdate() {
		window.location.reload();
	}
</script>

<svelte:document onvisibilitychange={checkForUpdate} />

{#if updated.current}
	<!-- Persistent by design: a prompt carrying an action must never auto-dismiss
		(WCAG 2.2.1), so this is a plain Toast with no close button and no timer.
		Shares the bottom band and z-layer with the status toasts; on the rare tick
		where a reload is pending and an action toast fires at the same time the two
		may overlap, which we accept rather than couple them across layouts.
		pointer-events-none on the full-width wrapper keeps taps outside the card from
		being swallowed; the card itself re-enables them. -->
	<div
		role="status"
		aria-live="polite"
		aria-atomic="true"
		class="pointer-events-none fixed inset-x-0 bottom-[calc(var(--bottom-nav-clearance)+0.5rem)] z-(--z-overlay) flex justify-center px-4 md:bottom-4 md:px-6 lg:px-8"
	>
		<div
			class="pointer-events-auto flex w-full max-w-sm flex-col gap-3 rounded-xl border border-border bg-card p-4 text-card-foreground shadow-lg"
		>
			<div class="flex items-center gap-3">
				<div
					class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
				>
					<RotateCw class="size-4 animate-spin" aria-hidden="true" />
				</div>
				<div class="text-sm leading-snug font-medium">Доступна новая версия приложения.</div>
			</div>
			<Button size="sm" class="w-full" onclick={applyUpdate}>Обновить</Button>
		</div>
	</div>
{/if}
