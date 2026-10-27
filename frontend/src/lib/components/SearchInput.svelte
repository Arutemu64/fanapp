<script lang="ts">
	import SearchIcon from '@lucide/svelte/icons/search';
	import X from '@lucide/svelte/icons/x';

	import * as InputGroup from '#lib/components/ui/input-group/index.js';
	import { m } from '#lib/paraglide/messages.js';

	interface Props {
		value: string;
		label: string;
		placeholder: string;
		name?: string;
		oninput?: () => void;
		onclear?: () => void;
	}

	let { value = $bindable(''), label, placeholder, name, oninput, onclear }: Props = $props();

	let input = $state<HTMLInputElement | null>(null);

	function clear() {
		value = '';
		input?.focus();
		onclear?.();
	}
</script>

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
