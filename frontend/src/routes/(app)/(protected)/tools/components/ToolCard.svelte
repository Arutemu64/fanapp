<script lang="ts">
	import type { Pathname } from '$app/types';
	import type { Component } from 'svelte';

	import { resolve } from '$app/paths';
	import { ArrowRight, Lock } from '@lucide/svelte';

	interface Props {
		title: string;
		description: string;
		icon: Component;
		href: Pathname;
		/** No permission for this tool: the card becomes a non-navigable, muted state. */
		locked?: boolean;
	}

	let { title, description, icon: Icon, href, locked = false }: Props = $props();

	// Same brand accent and shape as the home cards so the two dashboards read as
	// one system; the locked variant only mutes it, keeping the layout identical.
	const ICON = 'bg-primary/10 text-primary';
	const ICON_LOCKED = 'bg-muted text-muted-foreground';

	const BASE =
		'group flex h-full flex-col rounded-2xl border p-4 text-left shadow-sm transition-colors';
	// The focus-visible ring ensures keyboard focus indicators are clearly visible on card links.
	const OPEN =
		'border-border bg-card hover:border-primary-300 hover:bg-primary-50/40 focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:outline-none dark:hover:border-primary-500 dark:hover:bg-primary-900/10';
	const LOCKED = 'cursor-not-allowed border-border bg-muted';
</script>

{#snippet body()}
	<span
		class={[
			'mb-3 flex h-11 w-11 items-center justify-center rounded-xl',
			locked ? ICON_LOCKED : ICON
		]}
	>
		<Icon class="size-5" aria-hidden="true" />
	</span>
	<h3
		class={[
			'text-sm font-semibold sm:text-base',
			locked ? 'text-muted-foreground' : 'text-foreground'
		]}
	>
		{title}
	</h3>
	<p class="mt-1 text-xs leading-relaxed text-muted-foreground sm:text-sm">
		{description}
	</p>
	{#if locked}
		<span class="mt-3 inline-flex items-center gap-1 text-xs font-medium text-muted-foreground">
			<Lock class="size-3.5" aria-hidden="true" />
			Нет доступа
		</span>
	{:else}
		<span class="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary">
			Открыть
			<ArrowRight
				class="size-3.5 transition-transform group-hover:translate-x-0.5"
				aria-hidden="true"
			/>
		</span>
	{/if}
{/snippet}

{#if locked}
	<!-- Non-navigable on purpose; the title explains the state on hover/focus without
	     inventing a channel to request access, which the app's admin model doesn't define. -->
	<div class={[BASE, LOCKED]} title="Права на этот инструмент не выданы">
		{@render body()}
	</div>
{:else}
	<a href={resolve(href)} class={[BASE, OPEN]}>
		{@render body()}
	</a>
{/if}
