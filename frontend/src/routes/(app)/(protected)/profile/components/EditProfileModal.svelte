<script lang="ts">
	import type { CurrentUserDto } from '#lib/api/generated/index.js';

	import * as Dialog from '#lib/components/ui/dialog/index.js';

	import EditProfileForm from './EditProfileForm.svelte';

	interface Props {
		user: CurrentUserDto;
		open: boolean;
	}

	let { user, open = $bindable(false) }: Props = $props();
</script>

<!-- The form owns its draft and mounts with the dialog content, so every open
     starts from the saved profile without an effect to reset it. -->
<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<EditProfileForm {user} onclose={() => (open = false)} />
	</Dialog.Content>
</Dialog.Root>
