<script lang="ts">
	import type { Snippet } from 'svelte';

	import { Switch } from '$lib/components/ui/switch';

	interface Props {
		id: string;
		title: string;
		/** Plain text only: it sits inside the <label>, where a link would steal the tap. */
		description: string;
		checked: boolean;
		disabled?: boolean;
		/** Hover hint for a disabled switch (desktop only — touch never shows it). */
		disabledHint?: string;
		onCheckedChange: (checked: boolean) => void;
		/** Extra content under the description, outside the label — links and buttons go here. */
		children?: Snippet;
	}

	let {
		id,
		title,
		description,
		checked,
		disabled = false,
		disabledHint,
		onCheckedChange,
		children
	}: Props = $props();

	let titleId = $derived(`${id}-title`);
	let descriptionId = $derived(`${id}-description`);
</script>

<!--
	The title and description are a <label for> the switch, so a tap anywhere on the
	text toggles it, as on a phone's settings screen (Material's SwitchListTile:
	"tapping anywhere in the tile toggles the switch"). The accessible name is the
	visible title alone (aria-labelledby wins over the label), so the spoken name
	matches what is on screen (WCAG 2.5.3) and the description is announced once,
	as the description.
-->
<div class="flex items-start justify-between gap-3 p-3 sm:p-4">
	<div class="min-w-0 flex-1">
		<label for={id} class={['block', disabled ? 'cursor-not-allowed' : 'cursor-pointer']}>
			<span id={titleId} class="block text-sm font-medium text-foreground">{title}</span>
			<span id={descriptionId} class="mt-1 block text-sm leading-relaxed text-muted-foreground">
				{description}
			</span>
		</label>
		{@render children?.()}
	</div>
	<!-- Controlled: the switch shows only what the parent says, so a toggle the parent
	     declines (a refused permission, a failed save) never leaves it flipped. -->
	<Switch
		{id}
		bind:checked={() => checked, onCheckedChange}
		aria-labelledby={titleId}
		aria-describedby={descriptionId}
		{disabled}
		title={disabledHint}
	/>
</div>
