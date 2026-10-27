<script lang="ts">
	import type { SVGAttributes } from 'svelte/elements';

	import Loader2Icon from '@lucide/svelte/icons/loader-2';

	// Deviates from upstream: Russian copy comes from Paraglide messages.
	import { m } from '#lib/paraglide/messages.js';
	import { cn } from '#lib/utils.js';

	let {
		class: className,
		role = 'status',
		name,
		color,
		stroke,
		className: legacyClassName,
		// Deviates from upstream: Russian default label.
		'aria-label': ariaLabel = m.common_loading(),
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
