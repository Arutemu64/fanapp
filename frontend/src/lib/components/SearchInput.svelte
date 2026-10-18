<script lang="ts">
	import { Search as SearchIcon, X } from '@lucide/svelte';

	import * as InputGroup from '#lib/components/ui/input-group/index.js';
	import { m } from '#lib/paraglide/messages.js';

	interface Props {
		value: string;
		/** Accessible name; the field has no visible label. */
		label: string;
		placeholder: string;
		name?: string;
		oninput?: () => void;
		/** Runs after the clear button has emptied the field. */
		onclear?: () => void;
	}

	let { value = $bindable(''), label, placeholder, name, oninput, onclear }: Props = $props();

	let input = $state<HTMLInputElement | null>(null);

	function clear() {
		value = '';
		// The button unmounts with the text, so focus goes back to the field
		// instead of dropping to the page.
		input?.focus();
		onclear?.();
	}
</script>

<!-- type="search" for the phone keyboard's search key; WebKit's own cancel button is
	hidden because the clear button below is the one with a 44px target and a
	Russian name. -->
<InputGroup.Root>
	<InputGroup.Addon>
		<SearchIcon aria-hidden="true" />
	</InputGroup.Addon>
	<InputGroup.Input
		bind:ref={input}
		bind:value
		type="search"
		{name}
		aria-label={label}
		{placeholder}
		autocomplete="off"
		autocapitalize="off"
		spellcheck={false}
		enterkeyhint="search"
		class="[&::-webkit-search-cancel-button]:hidden"
		{oninput}
	/>
	{#if value}
		<InputGroup.Addon align="inline-end">
			<InputGroup.Button
				size="icon-sm"
				class="size-11"
				onclick={clear}
				aria-label={m.common_clear_search()}
			>
				<X />
			</InputGroup.Button>
		</InputGroup.Addon>
	{/if}
</InputGroup.Root>
