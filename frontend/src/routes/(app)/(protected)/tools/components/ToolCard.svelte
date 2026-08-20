<script lang="ts">
	import type { Pathname } from '$app/types';
	import type { Component } from 'svelte';

	import { resolve } from '$app/paths';
	import { ArrowRightOutline, LockOutline } from 'flowbite-svelte-icons';

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
	const ICON = 'bg-primary-50 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400';
	const ICON_LOCKED = 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-600';

	const BASE =
		'group flex h-full flex-col rounded-2xl border p-4 text-left shadow-sm transition-colors';
	// The focus-visible ring mirrors flowbiteTheme.card: hand-rolled card links
	// don't inherit it, and without it the keyboard focus indicator is missing.
	const OPEN =
		'border-gray-200 bg-white hover:border-primary-300 hover:bg-primary-50/40 focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:outline-none dark:border-gray-800 dark:bg-gray-900 dark:hover:border-primary-500 dark:hover:bg-primary-900/10';
	const LOCKED =
		'cursor-not-allowed border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-900/50';
</script>

{#snippet body()}
	<span
		class={[
			'mb-3 flex h-11 w-11 items-center justify-center rounded-xl',
			locked ? ICON_LOCKED : ICON
		]}
	>
		<Icon class="h-5 w-5" aria-hidden="true" />
	</span>
	<h3
		class={[
			'text-sm font-semibold sm:text-base',
			locked ? 'text-gray-500 dark:text-gray-500' : 'text-gray-900 dark:text-white'
		]}
	>
		{title}
	</h3>
	<p
		class={[
			'mt-1 text-xs leading-relaxed sm:text-sm',
			locked ? 'text-gray-400 dark:text-gray-600' : 'text-gray-600 dark:text-gray-400'
		]}
	>
		{description}
	</p>
	{#if locked}
		<span
			class="mt-3 inline-flex items-center gap-1 text-xs font-medium text-gray-400 dark:text-gray-600"
		>
			<LockOutline class="h-3.5 w-3.5" aria-hidden="true" />
			Нет доступа
		</span>
	{:else}
		<span
			class="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary-600 dark:text-primary-400"
		>
			Открыть
			<ArrowRightOutline
				class="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5"
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
