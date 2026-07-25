<!--
@component
Password field with a show/hide toggle and a lock icon.

`autocomplete` is required, not defaulted: the browser needs `current-password`
on a login form and `new-password` on registration or a change-password form,
and getting it wrong breaks password-manager behaviour. `revealLabel` is the
Russian noun interpolated into the toggle's aria-label.
-->
<script lang="ts">
	import { Input } from 'flowbite-svelte';
	import { EyeOutline, EyeSlashOutline, LockSolid } from 'flowbite-svelte-icons';

	interface Props {
		value: string;
		id: string;
		name: string;
		autocomplete: 'current-password' | 'new-password';
		// Noun used in the toggle's aria-label, e.g. "Показать {revealLabel}".
		revealLabel?: string;
		placeholder?: string;
		required?: boolean;
		disabled?: boolean;
		maxlength?: number;
		color?: 'red' | undefined;
		oninput?: () => void;
	}

	let {
		value = $bindable(''),
		id,
		name,
		autocomplete,
		revealLabel = 'пароль',
		placeholder = '••••••••',
		required = false,
		disabled = false,
		maxlength,
		color,
		oninput
	}: Props = $props();

	let show = $state(false);
</script>

<Input
	{id}
	{name}
	type={show ? 'text' : 'password'}
	bind:value
	{placeholder}
	{autocomplete}
	{required}
	{disabled}
	{maxlength}
	class="ps-9"
	{color}
	{oninput}
>
	{#snippet left()}
		<LockSolid class="h-5 w-5" />
	{/snippet}
	{#snippet right()}
		<button
			type="button"
			class="pointer-events-auto -mr-2 flex min-h-11 min-w-11 items-center justify-center rounded-lg hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 dark:hover:bg-gray-700"
			onclick={() => (show = !show)}
			aria-label={show ? `Скрыть ${revealLabel}` : `Показать ${revealLabel}`}
			aria-pressed={show}
		>
			{#if show}
				<EyeOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			{:else}
				<EyeSlashOutline class="h-5 w-5 text-gray-500 dark:text-gray-400" />
			{/if}
		</button>
	{/snippet}
</Input>
