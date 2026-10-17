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

<!--
	Wraps instead of truncating: the trailing digits are what tell two generated
	namesakes apart, so an ellipsis would hide the one part that identifies the
	player. <wbr> marks the word seams (it adds no character to the text or the
	accessible name); wrap-anywhere still breaks a long seamless name rather than
	letting it overflow a flex row.
-->
<span class={cn('wrap-anywhere', className)}
	>@{#each words as word, index (index)}{#if index > 0}<wbr />{/if}{word}{/each}</span
>
