<script lang="ts">
	import { cn } from '$lib/utils.js';
	import { PinInput as InputOTPPrimitive } from 'bits-ui';

	let {
		ref = $bindable(null),
		cell,
		class: className,
		...restProps
	}: InputOTPPrimitive.CellProps = $props();
</script>

<InputOTPPrimitive.Cell
	{cell}
	bind:ref
	data-slot="input-otp-slot"
	class={cn(
		// Signature OTP box: 44px tap target (h-11) with a large bold digit, sm:h-12 on
		// desktop (DESIGN.md §5 "OTP"). Deviates from the vega default (size-9 text-sm) —
		// keep on a shadcn-svelte update.
		'relative flex h-11 w-11 items-center justify-center border-y border-e border-input text-lg font-bold transition-all outline-none first:rounded-s-md first:border-s last:rounded-e-md aria-invalid:border-destructive sm:h-12 dark:bg-input/30',
		cell.isActive &&
			'z-10 border-ring ring-[3px] ring-ring/50 ring-offset-background aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40',
		className
	)}
	{...restProps}
>
	{cell.char}
	{#if cell.hasFakeCaret}
		<div class="pointer-events-none absolute inset-0 flex items-center justify-center">
			<div class="h-4 w-px animate-caret-blink bg-foreground duration-1000"></div>
		</div>
	{/if}
</InputOTPPrimitive.Cell>
