<script lang="ts">
	import { Input } from 'flowbite-svelte';
	import { onMount } from 'svelte';

	interface Props {
		value: string;
		disabled?: boolean;
		hasError?: boolean;
		onComplete?: (code: string) => void | Promise<void>;
		onInput?: () => void;
	}

	let {
		value = $bindable(''),
		disabled = false,
		hasError = false,
		onComplete,
		onInput
	}: Props = $props();

	let codeDigits = $state(['', '', '', '', '', '']);
	let container = $state<HTMLDivElement | undefined>(undefined);

	// Two-way bridge between the single `value` prop and the six digit boxes.
	// An $effect (not $derived) is the right escape hatch here: the boxes are
	// independently writable local state, and we only mirror `value` → boxes for
	// external changes (a parent reset to ''); the boxes → `value` direction goes
	// through updateValue() on input. Syncing external changes of `value` down to
	// the individual digit inputs:
	$effect(() => {
		const val = value || '';
		for (let i = 0; i < 6; i++) {
			codeDigits[i] = val[i] || '';
		}

		if (val === '' && container) {
			const inputs = container.querySelectorAll('input');
			const firstInput = inputs?.[0] as HTMLInputElement;
			firstInput?.focus();
		}
	});

	// Synchronize internal digit changes back up to the external `value` prop
	function updateValue() {
		const newValue = codeDigits.join('');
		value = newValue;
		onInput?.();

		if (newValue.length === 6 && onComplete) {
			void onComplete(newValue);
		}
	}

	function handlePinKeyup(event: KeyboardEvent, index: number) {
		if (!container) return;
		const inputs = container.querySelectorAll('input');
		if (!inputs) return;

		if (event.key === 'Backspace' && codeDigits[index] === '' && index > 0) {
			const prevInput = inputs[index - 1] as HTMLInputElement;
			prevInput?.focus();
			return;
		}

		if (codeDigits[index] !== '' && index < 5 && /^\d$/.test(event.key)) {
			const nextInput = inputs[index + 1] as HTMLInputElement;
			nextInput?.focus();
		}
	}

	function handlePinPaste(event: ClipboardEvent) {
		event.preventDefault();
		const pasteData = event.clipboardData?.getData('text') ?? '';
		const digits = pasteData.replace(/\D/g, '').slice(0, 6);

		if (!digits) return;

		for (let i = 0; i < 6; i++) {
			codeDigits[i] = digits[i] || '';
		}

		updateValue();

		if (!container) return;
		const inputs = container.querySelectorAll('input');
		if (!inputs) return;

		const nextEmptyIndex = codeDigits.findIndex((d) => d === '');
		if (nextEmptyIndex !== -1) {
			const targetInput = inputs[nextEmptyIndex] as HTMLInputElement;
			targetInput?.focus();
		} else {
			const lastInput = inputs[5] as HTMLInputElement;
			lastInput?.focus();
		}
	}

	onMount(() => {
		if (container) {
			const inputs = container.querySelectorAll('input');
			const firstInput = inputs?.[0] as HTMLInputElement;
			firstInput?.focus();
		}
	});
</script>

<div bind:this={container} class="flex justify-center space-x-2 rtl:space-x-reverse">
	{#each [0, 1, 2, 3, 4, 5] as i (i)}
		<div>
			<label for={`otp-digit-${i}`} class="sr-only">Цифра {i + 1}</label>
			<Input
				type="text"
				inputmode="numeric"
				autocomplete={i === 0 ? 'one-time-code' : 'off'}
				maxlength={1}
				id={`otp-digit-${i}`}
				bind:value={codeDigits[i]}
				onkeyup={(e) => handlePinKeyup(e, i)}
				onpaste={i === 0 ? handlePinPaste : undefined}
				oninput={() => {
					codeDigits[i] = (codeDigits[i] || '').replace(/\D/g, '');
					updateValue();
				}}
				{disabled}
				color={hasError ? 'red' : undefined}
				class="block h-11 w-11 py-3 text-center text-lg font-extrabold sm:h-12 sm:w-12 sm:text-xl"
				required
			/>
		</div>
	{/each}
</div>
