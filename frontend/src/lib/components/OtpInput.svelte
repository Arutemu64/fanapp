<script lang="ts">
	import { Input } from 'flowbite-svelte';

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

	let container = $state<HTMLDivElement | undefined>(undefined);

	// `value` is the single source of truth; the boxes are a view of it, so there is
	// no second copy to keep in step. Writing to a derived overrides it until its
	// expression changes — which is exactly the behaviour the boxes need: a stray
	// keystroke is held long enough for the binding to correct the DOM, while a
	// parent clearing `value` re-evaluates this and the boxes follow.
	let codeDigits = $derived.by(() => {
		const val = value || '';
		return Array.from({ length: 6 }, (_, i) => val[i] ?? '');
	});

	function focusBox(index: number) {
		container?.querySelectorAll('input')[index]?.focus();
	}

	// Pure DOM side effect, not state syncing: put the caret back in the first box
	// whenever the code is empty — on mount, and when a parent drops a code the
	// server rejected — so the user can retype without reaching for the field.
	$effect(() => {
		if (value === '') {
			focusBox(0);
		}
	});

	function commit(next: string) {
		value = next;
		onInput?.();

		if (next.length === 6 && onComplete) {
			void onComplete(next);
		}
	}

	// `raw` widens to undefined because flowbite's Input clears its value that way.
	function setDigit(index: number, raw: string | undefined) {
		const next = [...codeDigits];
		next[index] = (raw || '').replace(/\D/g, '');
		// Override the derived so the box reflects the sanitised digit even when
		// `value` itself is unchanged (typing a letter into an empty box).
		codeDigits = next;
		commit(next.join(''));
	}

	function handlePinKeyup(event: KeyboardEvent, index: number) {
		if (event.key === 'Backspace' && codeDigits[index] === '' && index > 0) {
			focusBox(index - 1);
			return;
		}

		if (codeDigits[index] !== '' && index < 5 && /^\d$/.test(event.key)) {
			focusBox(index + 1);
		}
	}

	function handlePinPaste(event: ClipboardEvent) {
		event.preventDefault();
		const pasteData = event.clipboardData?.getData('text') ?? '';
		const digits = pasteData.replace(/\D/g, '').slice(0, 6);

		if (!digits) return;

		commit(digits);

		const nextEmptyIndex = codeDigits.findIndex((d) => d === '');
		focusBox(nextEmptyIndex === -1 ? 5 : nextEmptyIndex);
	}
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
				bind:value={() => codeDigits[i], (raw: string | undefined) => setDigit(i, raw)}
				onkeyup={(e) => handlePinKeyup(e, i)}
				onpaste={i === 0 ? handlePinPaste : undefined}
				{disabled}
				color={hasError ? 'red' : undefined}
				class="block h-11 w-11 py-3 text-center text-lg font-extrabold sm:h-12 sm:w-12 sm:text-xl"
				required
			/>
		</div>
	{/each}
</div>
