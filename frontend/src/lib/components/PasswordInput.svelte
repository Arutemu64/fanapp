<script lang="ts">
	import * as InputGroup from '$lib/components/ui/input-group';
	import { Eye, EyeOff, Lock } from '@lucide/svelte';

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
		readonly?: boolean;
		maxlength?: number;
		color?: 'red' | undefined;
		// Id of the error or hint that describes the field (aria-describedby).
		describedby?: string;
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
		readonly = false,
		maxlength,
		color,
		describedby,
		oninput
	}: Props = $props();

	let show = $state(false);
	let invalid = $derived(color === 'red');
</script>

<InputGroup.Root>
	<InputGroup.Addon>
		<Lock aria-hidden="true" />
	</InputGroup.Addon>
	<InputGroup.Input
		{id}
		{name}
		type={show ? 'text' : 'password'}
		bind:value
		{placeholder}
		{autocomplete}
		{required}
		{disabled}
		{readonly}
		{maxlength}
		aria-invalid={invalid ? true : undefined}
		aria-describedby={describedby}
		{oninput}
	/>
	<InputGroup.Addon align="inline-end">
		<InputGroup.Button
			size="icon-sm"
			{disabled}
			onclick={() => (show = !show)}
			aria-label={show ? `Скрыть ${revealLabel}` : `Показать ${revealLabel}`}
			aria-pressed={show}
		>
			{#if show}
				<Eye />
			{:else}
				<EyeOff />
			{/if}
		</InputGroup.Button>
	</InputGroup.Addon>
</InputGroup.Root>
