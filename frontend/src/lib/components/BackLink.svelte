<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { ArrowLeft } from '@lucide/svelte';

	interface Props {
		/** Parent route this detail page returns to. */
		href: string;
		/** Visible text; also the button's accessible name so the arrow icon stays decorative. */
		label: string;
	}

	let { href, label }: Props = $props();
</script>

<Button {href} variant="outline" size="sm" class="mb-2 sm:mb-3" aria-label={label}>
	<ArrowLeft data-icon="inline-start" />
	{label}
</Button>
