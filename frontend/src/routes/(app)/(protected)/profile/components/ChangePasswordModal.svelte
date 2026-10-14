<script lang="ts">
	import * as Dialog from '#lib/components/ui/dialog/index.js';

	import ChangePasswordForm from './ChangePasswordForm.svelte';

	interface Props {
		open: boolean;
		hasPassword?: boolean;
	}

	let { open = $bindable(false), hasPassword = true }: Props = $props();
</script>

<!-- The form owns its state and mounts with the dialog content, so every open
     starts blank without an effect to reset it. -->
<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<ChangePasswordForm {hasPassword} onclose={() => (open = false)} />
	</Dialog.Content>
</Dialog.Root>
