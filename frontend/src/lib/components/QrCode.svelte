<script lang="ts">
	import { qrPath } from '#lib/utils/qrPath.js';

	interface Props {
		value: string;
		label: string;
		class?: string;
	}

	let { value, label, class: className }: Props = $props();

	let qr = $derived(qrPath(value));
</script>

<svg
	viewBox="0 0 {qr.size} {qr.size}"
	role="img"
	aria-label={label}
	shape-rendering="crispEdges"
	class={['block bg-white', className]}
>
	<path d={qr.d} fill="#000" />
</svg>
