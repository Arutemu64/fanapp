<script lang="ts">
	import { Eye, EyeOff, Lock } from '@lucide/svelte';

	import * as InputGroup from '#lib/components/ui/input-group/index.js';

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
		// Apple Password AutoFill hint: makes the generated password fit the
		// backend's length rules. Ignored by other browsers.
		passwordrules?: string;
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
		passwordrules,
		color,
		describedby,
		oninput
	}: Props = $props();

	let show = $state(false);
	// `passwordrules` is missing from Svelte's input attribute types, so it rides in
	// through a spread.
	let extraAttributes = $derived(passwordrules ? { passwordrules } : {});
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
		{...extraAttributes}
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
