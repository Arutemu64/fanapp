<script lang="ts">
	import { Button } from 'flowbite-svelte';
	import { ArrowLeftOutline } from 'flowbite-svelte-icons';

	interface Props {
		/** Parent route this detail page returns to. */
		href: string;
		/** Visible text; also the button's accessible name so the arrow icon stays decorative. */
		label: string;
	}

	let { href, label }: Props = $props();
</script>

<Button {href} outline size="sm" color="alternative" class="mb-2 sm:mb-3" aria-label={label}>
	<ArrowLeftOutline class="mr-1 h-4 w-4" />
	{label}
</Button>
