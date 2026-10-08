<script lang="ts">
	import { RadioGroup as RadioGroupPrimitive } from 'bits-ui';

	import { cn, type WithoutChildrenOrChild } from '#lib/utils.js';

	let {
		ref = $bindable(null),
		class: className,
		...restProps
	}: WithoutChildrenOrChild<RadioGroupPrimitive.ItemProps> = $props();
</script>

<!--
	Styled on `data-[state=checked]`, the attribute bits-ui 2 sets on a radio item;
	the registry's `data-checked:` variant targets an attribute this version never
	writes, so the checked dot would never show. The `after:` pseudo extends the tap
	target past the 16px circle, as in `checkbox.svelte`. Keep both on a
	`shadcn-svelte update` merge.
-->
<RadioGroupPrimitive.Item
	bind:ref
	data-slot="radio-group-item"
	class={cn(
		'peer relative flex aspect-square size-4 shrink-0 items-center justify-center rounded-full border border-input shadow-xs transition-shadow outline-none after:absolute after:-inset-x-3 after:-inset-y-2 focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 data-[state=checked]:border-primary data-[state=checked]:bg-primary dark:bg-input/30 dark:aria-invalid:ring-destructive/40 dark:data-[state=checked]:bg-primary',
		className
	)}
	{...restProps}
>
	{#snippet children({ checked })}
		<span data-slot="radio-group-indicator" class="flex items-center justify-center">
			{#if checked}
				<span class="size-1.5 rounded-full bg-primary-foreground"></span>
			{/if}
		</span>
	{/snippet}
</RadioGroupPrimitive.Item>
