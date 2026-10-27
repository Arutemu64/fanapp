<script lang="ts">
	import { page } from '$app/state';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import CircleAlert from '@lucide/svelte/icons/circle-alert';
	import House from '@lucide/svelte/icons/house';
	import Lock from '@lucide/svelte/icons/lock';
	import RotateCw from '@lucide/svelte/icons/rotate-cw';

	import { Button } from '#lib/components/ui/button/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { probeReachability, reachability } from '#lib/services/reachability.js';
	import { statusTitle } from '#lib/utils/errorTitle.js';

	type Variant = 'fullscreen' | 'inline';

	let {
		variant = 'fullscreen',
		error,
		onRetry
	}: {
		variant?: Variant;
		error?: Omit<App.Error, 'status'> & { status?: number };
		onRetry?: () => void;
	} = $props();

	let shownError = $derived(error ?? page.error);
	let status = $derived(error === undefined ? page.status : error.status);
	let errorMessage = $derived(shownError?.message);
	let errorId = $derived(shownError?.errorId);

	let online = $derived(reachability.current);
	let offline = $derived(!online && status !== 403 && status !== 404);
	let canRetry = $derived(
		offline || onRetry !== undefined || (status !== undefined && status >= 500)
	);

	let deviceOffline = $derived(!reachability.deviceOnline);

	let title = $derived.by(() => {
		if (!offline) return statusTitle(status);
		return deviceOffline ? m.connection_no_internet() : m.connection_no_server();
	});

	let StatusIcon = $derived(status === 403 ? Lock : CircleAlert);
	let iconColorClass = $derived(
		offline ? 'bg-warning/15 text-warning' : 'bg-destructive/15 text-destructive'
	);

	let description = $derived.by(() => {
		if (offline && deviceOffline) return m.error_state_offline_hint();
		if (offline) return m.error_state_server_offline_hint();
		if (errorMessage) return errorMessage;
		if (status === 403) return m.error_state_forbidden();
		if (status === 404) return m.error_state_not_found();
		return m.error_state_unexpected();
	});

	let wrapperClass = $derived(
		variant === 'fullscreen'
			? 'flex min-h-svh items-center justify-center bg-background px-4 py-6 sm:py-10'
			: 'flex min-h-[60svh] items-center justify-center px-4 py-6'
	);

	function handleGoBack() {
		window.history.back();
	}

	function handleRetry() {
		if (onRetry) {
			if (!online) void probeReachability();
			onRetry();
			return;
		}
		window.location.reload();
	}
</script>

<div class={wrapperClass}>
	<Card.Root class="w-full max-w-md p-6 text-center sm:p-8">
		<div class="flex flex-col items-center justify-center">
			<div class="mb-4 flex size-16 items-center justify-center rounded-full {iconColorClass}">
				<StatusIcon class="size-8" />
			</div>

			{#if offline}
				<span class="mb-1 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
					{m.error_state_offline_title()}
				</span>
			{:else if status !== undefined}
				<span class="mb-1 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
					{m.error_state_status_title({ status })}
				</span>
			{/if}

			<h2 class="mb-2 text-headline text-foreground">
				{title}
			</h2>

			<p class="mb-6 text-body text-muted-foreground">
				{description}
			</p>

			{#if errorId}
				<p class="-mt-4 mb-6 text-xs text-muted-foreground">
					{m.error_state_code_label()} <span class="font-mono select-all">{errorId}</span>
				</p>
			{/if}

			<div class="flex w-full flex-col gap-2">
				{#if canRetry}
					<Button class="w-full" onclick={handleRetry}>
						<RotateCw data-icon="inline-start" />
						{m.common_try_again()}
					</Button>
				{/if}

				<Button href="/" variant={canRetry ? 'outline' : 'default'} class="w-full">
					<House data-icon="inline-start" />
					{m.common_to_home()}
				</Button>

				<Button type="button" variant="ghost" class="w-full" onclick={handleGoBack}>
					<ArrowLeft data-icon="inline-start" />
					{m.common_go_back()}
				</Button>
			</div>
		</div>
	</Card.Root>
</div>
