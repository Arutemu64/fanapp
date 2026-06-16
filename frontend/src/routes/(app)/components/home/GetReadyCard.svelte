<script lang="ts">
	import type { Component } from 'svelte';
	import type { Pathname } from '$app/types';
	import { resolve } from '$app/paths';
	import ArrowRightIcon from '~icons/lucide/arrow-right';

	interface Props {
		title: string;
		description: string;
		icon: Component;
		/** Полные классы для «пузыря» иконки (фон + цвет). */
		iconClass: string;
		/** Полные классы ховера для рамки/фона карточки. */
		hoverClass: string;
		/** Текст действия внизу карточки. */
		actionLabel?: string;
		href?: Pathname;
		onclick?: () => void;
	}

	let {
		title,
		description,
		icon: Icon,
		iconClass,
		hoverClass,
		actionLabel = 'Открыть',
		href,
		onclick
	}: Props = $props();
</script>

{#snippet body()}
	<span
		class={[
			'mb-3 flex h-11 w-11 items-center justify-center rounded-xl transition-transform group-hover:scale-105',
			iconClass
		]}
	>
		<Icon class="h-5 w-5" aria-hidden="true" />
	</span>
	<h3 class="text-sm font-semibold text-gray-900 sm:text-base dark:text-white">
		{title}
	</h3>
	<p class="mt-1 text-xs leading-relaxed text-gray-500 sm:text-sm dark:text-gray-400">
		{description}
	</p>
	<span
		class="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary-600 dark:text-primary-400"
	>
		{actionLabel}
		<!-- Arrow implies navigation; only show it for link cards, not action buttons -->
		{#if href}
			<ArrowRightIcon
				class="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5"
				aria-hidden="true"
			/>
		{/if}
	</span>
{/snippet}

{#if href}
	<a
		href={resolve(href)}
		class={[
			'group flex h-full flex-col rounded-2xl border border-gray-200 bg-white p-4 text-left shadow-sm transition-colors dark:border-gray-800 dark:bg-gray-900',
			hoverClass
		]}
	>
		{@render body()}
	</a>
{:else}
	<button
		type="button"
		{onclick}
		class={[
			'group flex h-full flex-col rounded-2xl border border-gray-200 bg-white p-4 text-left shadow-sm transition-colors dark:border-gray-800 dark:bg-gray-900',
			hoverClass
		]}
	>
		{@render body()}
	</button>
{/if}
