<script lang="ts">
	import { cn } from '#lib/utils.js';
	import { splitUsernameWords } from '#lib/utils/users.js';

	interface Props {
		username: string;
		class?: string;
	}

	let { username, class: className }: Props = $props();

	const words = $derived(splitUsernameWords(username));
</script>

<span class={cn('wrap-anywhere', className)}
	>@{#each words as word, index (index)}{#if index > 0}<wbr />{/if}{word}{/each}</span
>
