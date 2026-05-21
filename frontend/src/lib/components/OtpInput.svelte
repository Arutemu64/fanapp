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

	// Local state for individual digits
	let codeDigits = $state(['', '', '', '', '', '']);
	let container = $state<HTMLDivElement | undefined>(undefined);

	// Synchronize external changes of `value` (e.g., reset from parent) down to individual digit inputs
	$effect(() => {
		const val = value || '';
		for (let i = 0; i < 6; i++) {
			codeDigits[i] = val[i] || '';
		}

		// If value is reset to empty, refocus the first input field
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

	// Handle Backspace navigation and auto-focusing on typing
	function handlePinKeyup(event: KeyboardEvent, index: number) {
		if (!container) return;
		const inputs = container.querySelectorAll('input');
		if (!inputs) return;

		// Move to previous box if Backspace is pressed in an empty box
		if (event.key === 'Backspace' && codeDigits[index] === '' && index > 0) {
			const prevInput = inputs[index - 1] as HTMLInputElement;
			prevInput?.focus();
			return;
		}

		// Move to next box if a digit has been typed
		if (codeDigits[index] !== '' && index < 5 && /^\d$/.test(event.key)) {
			const nextInput = inputs[index + 1] as HTMLInputElement;
			nextInput?.focus();
		}
	}

	// Handle clipboard paste across all 6 input fields
	function handlePinPaste(event: ClipboardEvent) {
		event.preventDefault();
		// @ts-expect-error - clipboardData is not standard on older browsers but standard today
		const windowClipboard = window.clipboardData;
		const pasteData =
			event.clipboardData?.getData('text') || windowClipboard?.getData('text') || '';
		const digits = pasteData.replace(/\D/g, '').slice(0, 6); // Extract up to 6 numeric digits

		if (!digits) return;

		// Fill the local digit boxes with pasted content
		for (let i = 0; i < 6; i++) {
			codeDigits[i] = digits[i] || '';
		}

		updateValue();

		if (!container) return;
		const inputs = container.querySelectorAll('input');
		if (!inputs) return;

		// Focus the next empty input, or the last one if completely filled
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
		// Automatically focus the first input block on mount
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
					// Ensure only numbers are entered in each cell
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
