<script lang="ts">
	import type { Snippet } from 'svelte';

	import { Switch } from '#lib/components/ui/switch/index.js';

	interface Props {
		id: string;
		title: string;
		description: string;
		checked: boolean;
		disabled?: boolean;
		blocked?: boolean;
		onCheckedChange: (checked: boolean) => void;
		children?: Snippet;
	}

	let {
		id,
		title,
		description,
		checked,
		disabled = false,
		blocked = false,
		onCheckedChange,
		children
	}: Props = $props();

	let titleId = $derived(`${id}-title`);
	let descriptionId = $derived(`${id}-description`);
</script>

<div class="flex items-start justify-between gap-3 p-3 sm:p-4">
	<div class="min-w-0 flex-1">
		<label
			for={id}
			class={['block', disabled || blocked ? 'cursor-not-allowed' : 'cursor-pointer']}
		>
			<span id={titleId} class="block text-base font-medium text-foreground">{title}</span>
			<span id={descriptionId} class="mt-1 block text-sm leading-relaxed text-muted-foreground">
				{description}
			</span>
		</label>
		{@render children?.()}
	</div>
	<Switch
		{id}
		bind:checked={() => checked, onCheckedChange}
		aria-labelledby={titleId}
		aria-describedby={descriptionId}
		{disabled}
		aria-disabled={blocked}
	/>
</div>
