<script lang="ts">
	import type { SVGAttributes } from 'svelte/elements';

	import Loader2Icon from '@lucide/svelte/icons/loader-2';

	// Deviates from upstream: built-in accessible names go through Paraglide
	// instead of fixed English text, so they follow the interface language.
	import { m } from '#lib/paraglide/messages.js';
	import { cn } from '#lib/utils.js';

	let {
		class: className,
		role = 'status',
		// we add name, color, and stroke for compatibility with different icon libraries props.
		// only forward them when set, otherwise `stroke: undefined` overrides the icon's `currentColor`
		name,
		color,
		stroke,
		className: legacyClassName,
		// Deviates from upstream: Russian default label.
		'aria-label': ariaLabel = m.loading(),
		...restProps
	}: SVGAttributes<SVGSVGElement> = $props();
</script>

<Loader2Icon
	{role}
	{...name != null ? { name } : {}}
	{...color != null ? { color } : {}}
	{...stroke != null ? { stroke } : {}}
	{...legacyClassName != null ? { className: legacyClassName } : {}}
	aria-label={ariaLabel}
	class={cn('size-4 animate-spin', className)}
	{...restProps}
/>
