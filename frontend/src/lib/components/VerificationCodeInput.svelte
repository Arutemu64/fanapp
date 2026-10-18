<script lang="ts">
	import { type PinInputCell, REGEXP_ONLY_DIGITS } from 'bits-ui';

	import * as InputOTP from '#lib/components/ui/input-otp/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import { m } from '#lib/paraglide/messages.js';

	interface Props {
		value: string;
		id: string;
		/** Shown under the boxes while there is no error. */
		hint: string;
		error?: string;
		/** A check or a resend is in flight. */
		busy?: boolean;
		onValueChange?: () => void;
		onComplete?: () => void;
	}

	let {
		value = $bindable(''),
		id,
		hint,
		error = '',
		busy = false,
		onValueChange,
		onComplete
	}: Props = $props();

	let hintId = $derived(`${id}-hint`);
</script>

<div class="flex flex-col items-center gap-2">
	<Label for={id}>{m.verification_code_label()}</Label>
	<!-- Read-only, not disabled, while busy so focus and the phone keyboard stay
		put; digits-only so a stray letter can't auto-submit a doomed code. -->
	<InputOTP.Root
		inputId={id}
		maxlength={6}
		pattern={REGEXP_ONLY_DIGITS}
		bind:value
		readonly={busy}
		aria-invalid={error ? true : undefined}
		aria-describedby={hintId}
		{onValueChange}
		{onComplete}
	>
		{#snippet children({ cells }: { cells: PinInputCell[] })}
			<InputOTP.Group>
				{#each cells.slice(0, 3) as cell, index (index)}
					<InputOTP.Slot {cell} class="size-11 text-lg font-bold sm:size-12 sm:text-xl" />
				{/each}
			</InputOTP.Group>
			<InputOTP.Separator />
			<InputOTP.Group>
				{#each cells.slice(3, 6) as cell, index (index + 3)}
					<InputOTP.Slot {cell} class="size-11 text-lg font-bold sm:size-12 sm:text-xl" />
				{/each}
			</InputOTP.Group>
		{/snippet}
	</InputOTP.Root>
	{#if error}
		<p id={hintId} role="alert" class="text-center text-sm text-destructive">{error}</p>
	{:else}
		<p id={hintId} class="text-center text-sm text-muted-foreground">{hint}</p>
	{/if}
</div>
