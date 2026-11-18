<script lang="ts">
	import { type PinInputCell, REGEXP_ONLY_DIGITS } from 'bits-ui';

	import * as InputOTP from '#lib/components/ui/input-otp/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import { m } from '#lib/paraglide/messages.js';

	interface Props {
		value: string;
		id: string;
		hint: string;
		error?: string;
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
	<InputOTP.Root
		inputId={id}
		maxlength={6}
		pattern={REGEXP_ONLY_DIGITS}
		bind:value
		readonly={busy}
		aria-invalid={error ? true : undefined}
		aria-describedby={hintId}
		class="grid w-full max-w-74 grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] gap-1 sm:max-w-80"
		{onValueChange}
		{onComplete}
	>
		{#snippet children({ cells }: { cells: PinInputCell[] })}
			<InputOTP.Group class="grid grid-cols-3">
				{#each cells.slice(0, 3) as cell, index (index)}
					<InputOTP.Slot {cell} class="w-full sm:text-xl" />
				{/each}
			</InputOTP.Group>
			<InputOTP.Separator class="[&_svg:not([class*='size-'])]:size-3" />
			<InputOTP.Group class="grid grid-cols-3">
				{#each cells.slice(3, 6) as cell, index (index + 3)}
					<InputOTP.Slot {cell} class="w-full sm:text-xl" />
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
