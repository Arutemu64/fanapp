<script lang="ts">
	import { cn } from '#lib/utils.js';
	import { getAvatarDataUri } from '#lib/utils/avatar.js';

	interface Props {
		seed: string;
		class?: string;
	}

	let { seed, class: className }: Props = $props();
</script>

<img
	src={getAvatarDataUri(seed)}
	alt=""
	class={cn('aspect-square shrink-0 rounded-full bg-muted object-cover', className)}
/>
