<script lang="ts">
	import { qrPath } from '#lib/utils/qrPath.js';

	interface Props {
		value: string;
		/** Accessible name; the code itself means nothing to a screen reader. */
		label: string;
		class?: string;
	}

	let { value, label, class: className }: Props = $props();

	let qr = $derived(qrPath(value));
</script>

<!-- Dark on white in both themes: scanners read a light-on-dark code poorly,
     so the code never follows the dark palette. crispEdges keeps neighbouring
     modules from showing hairline seams when the SVG is scaled. -->
<svg
	viewBox="0 0 {qr.size} {qr.size}"
	role="img"
	aria-label={label}
	shape-rendering="crispEdges"
	class={['block bg-white', className]}
>
	<path d={qr.d} fill="#000" />
</svg>
