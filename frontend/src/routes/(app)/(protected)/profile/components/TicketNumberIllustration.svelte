<script lang="ts" module>
	// Bar and gap widths of a made-up barcode: it only has to read as "a barcode",
	// so a fixed pattern beats generating one.
	const PATTERN = [2, 1, 1, 2, 3, 1, 1, 1, 2, 2, 1, 3, 1, 1, 2, 1, 3, 2, 1, 1, 1, 2, 2, 1];
	const BAR_UNIT = 4;
	// Centres the bars over the number's 152-wide frame in the 200-wide viewBox.
	const BARS_LEFT = 24;

	// Even entries are bars, odd ones the gaps between them.
	const BARS: { x: number; width: number }[] = [];
	let x = BARS_LEFT;
	for (const [index, units] of PATTERN.entries()) {
		const width = units * BAR_UNIT;
		if (index % 2 === 0) {
			BARS.push({ x, width });
		}
		x += width;
	}
</script>

<!-- Decorative: the hint beside it says the same in words. -->
<div class="flex justify-center rounded-lg bg-muted p-3" aria-hidden="true">
	<svg viewBox="0 0 200 84" class="w-48">
		{#each BARS as bar (bar.x)}
			<rect x={bar.x} y="6" width={bar.width} height="42" class="fill-foreground" />
		{/each}
		<rect
			x="24"
			y="54"
			width="152"
			height="24"
			rx="6"
			class="fill-primary/10 stroke-primary"
			stroke-width="2"
		/>
		<text
			x="100"
			y="71"
			text-anchor="middle"
			class="fill-primary font-mono text-xs font-semibold"
			letter-spacing="1">1234 5678 9012</text
		>
	</svg>
</div>
