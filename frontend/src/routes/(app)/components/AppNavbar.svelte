<script lang="ts">
	import { page } from '$app/state';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';

	import type { CurrentUserDto } from '#lib/api/generated/index.js';

	import { Button } from '#lib/components/ui/button/index.js';
	import { tabHref } from '#lib/utils/nav.js';
	import { resolvePath } from '#lib/utils/paths.js';

	import NotificationBell from './NotificationBell.svelte';

	let pageTitle = $derived(page.data.title);
	let back = $derived(page.data.back);
	let actions = $derived(page.data.actions ?? []);

	interface Props {
		user: CurrentUserDto | null;
		contentScrolled: boolean;
		lastSearches: Readonly<Record<string, string>>;
	}

	let { user, contentScrolled, lastSearches }: Props = $props();
</script>

<header
	class={[
		'flex items-center justify-between gap-2 border-b bg-background/80 px-4 py-2.5 pt-[calc(0.625rem+env(safe-area-inset-top))] transition-colors duration-300 select-none [-webkit-touch-callout:none] sm:px-6 reduced-transparency:bg-background',
		contentScrolled ? 'border-border/50' : 'border-transparent'
	]}
>
	<div class="flex min-h-11 min-w-0 flex-1 items-center gap-1">
		{#if back}
			<Button
				href={tabHref(back.href, lastSearches)}
				variant="ghost"
				size="icon"
				class="-ml-2"
				aria-label={back.label}
			>
				<ArrowLeft class="size-5" />
			</Button>
		{/if}
		{#if pageTitle}
			<h1 class="line-clamp-2 text-headline wrap-break-word text-foreground">
				{pageTitle}
			</h1>
		{/if}
	</div>

	{#each actions as action (action.href)}
		<Button href={resolvePath(action.href)} variant="ghost" size="icon" aria-label={action.label}>
			<action.icon class="size-5" />
		</Button>
	{/each}

	{#if user}
		<svelte:boundary>
			<NotificationBell />
			{#snippet failed()}{/snippet}
		</svelte:boundary>
	{/if}
</header>
