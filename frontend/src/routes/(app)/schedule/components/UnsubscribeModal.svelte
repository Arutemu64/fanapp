<script lang="ts">
	import type { ScheduleEventWithSubscription } from '#lib/types/schedule.js';

	import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';

	import UnsubscribeForm from './UnsubscribeForm.svelte';

	interface Props {
		open: boolean;
		event: ScheduleEventWithSubscription;
	}
	let { open = $bindable(), event }: Props = $props();
</script>

<!-- AlertDialog (role="alertdialog"), not Dialog: a confirmation that must force an
	explicit choice and not dismiss on an outside click. The confirm is a plain Button
	(not AlertDialog.Action) because the request is fired in the form and a failure
	must keep the dialog open to show formError — Action would auto-close and drop
	the message. The form owns its error and mounts with the dialog content, so every
	open starts clean without an effect to reset it. -->
<AlertDialog.Root bind:open>
	<AlertDialog.Content>
		<UnsubscribeForm {event} onclose={() => (open = false)} />
	</AlertDialog.Content>
</AlertDialog.Root>
