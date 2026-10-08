<script lang="ts">
	import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';

	interface Props {
		open: boolean;
		title: string;
		description: string;
		/** Names the action ("Заменить программу"), never a bare "Да" (NN/g). */
		confirmLabel: string;
		/** Red confirm for actions that delete or switch something off. */
		destructive?: boolean;
		onconfirm: () => void;
	}

	let {
		open = $bindable(),
		title,
		description,
		confirmLabel,
		destructive = false,
		onconfirm
	}: Props = $props();
</script>

<!-- The toolbox's one confirm step, kept for actions that reach many people or
     can't be taken back: a mass mailing, replacing the programme, closing voting.
     Asking on routine actions trains people to tap through, so nothing else here
     confirms (https://www.nngroup.com/articles/confirmation-dialog/). AlertDialog,
     not Dialog: an outside tap must not count as a choice, and Cancel comes first
     so the safe option takes focus (docs/frontend.md "Confirmations"). -->
<AlertDialog.Root bind:open>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>{title}</AlertDialog.Title>
			<AlertDialog.Description>{description}</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>Отмена</AlertDialog.Cancel>
			<AlertDialog.Action variant={destructive ? 'destructive' : 'default'} onclick={onconfirm}>
				{confirmLabel}
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
