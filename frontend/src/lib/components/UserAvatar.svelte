<script lang="ts">
	import { cn } from '#lib/utils.js';
	import { getAvatarDataUri } from '#lib/utils/avatar.js';

	interface Props {
		seed: string;
		class?: string;
	}

	let { seed, class: className }: Props = $props();
</script>

<!-- Decorative: the username always sits next to it. Size comes from the caller. -->
<img
	src={getAvatarDataUri(seed)}
	alt=""
	class={cn('aspect-square shrink-0 rounded-full bg-muted object-cover', className)}
/>
