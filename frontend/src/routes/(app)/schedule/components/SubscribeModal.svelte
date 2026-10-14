<script lang="ts">
	import type { ScheduleEventFullDto } from '#lib/api/generated/index.js';

	import * as Dialog from '#lib/components/ui/dialog/index.js';

	import SubscribeForm from './SubscribeForm.svelte';

	interface Props {
		open: boolean;
		event: ScheduleEventFullDto;
	}
	let { open = $bindable(), event }: Props = $props();
</script>

<!-- The form owns its state and mounts with the dialog content, so every open
     starts from the default counter without an effect to reset it. -->
<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<SubscribeForm {event} onclose={() => (open = false)} />
	</Dialog.Content>
</Dialog.Root>
