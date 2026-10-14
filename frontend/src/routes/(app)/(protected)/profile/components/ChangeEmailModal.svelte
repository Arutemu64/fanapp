<script lang="ts">
	import * as Dialog from '#lib/components/ui/dialog/index.js';

	import ChangeEmailForm from './ChangeEmailForm.svelte';

	interface Props {
		open: boolean;
		currentEmail?: string | null;
	}

	let { open = $bindable(false), currentEmail }: Props = $props();
</script>

<!-- The form owns its state and mounts with the dialog content, so every open
     starts at the email step without an effect to reset it. -->
<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<ChangeEmailForm {currentEmail} onclose={() => (open = false)} />
	</Dialog.Content>
</Dialog.Root>
