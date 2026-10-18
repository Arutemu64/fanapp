<script lang="ts">
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import ScanLine from '@lucide/svelte/icons/scan-line';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { CurrentUserDto } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		getCurrentUserQueryKey,
		getVotingStatusQueryKey,
		linkTicketMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import BarcodeScannerDialog from '#lib/components/BarcodeScannerDialog.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	import SettingsSection from './SettingsSection.svelte';
	import TicketNumberIllustration from './TicketNumberIllustration.svelte';

	interface Props {
		user: CurrentUserDto;
	}

	let { user }: Props = $props();
	const queryClient = useQueryClient();
	const toastService = getToastService();

	const linkMutation = createMutation(() => ({
		...linkTicketMutation(),
		onSuccess: () => {
			// A linked ticket is what lets the user vote, so the voting status moves with it.
			void queryClient.invalidateQueries({ queryKey: getVotingStatusQueryKey() });
			return queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() });
		}
	}));

	// Linking a ticket is a mutation — online only. A linked ticket still shows.
	const offlineGate = offlineWriteGate();

	// The QR code and both Code 128 stubs on a TicketsCloud ticket all encode the
	// number printed beside them, so either scans straight into the field.
	const TICKET_FORMATS = ['QRCode', 'Code128'] as const;

	let barcode = $state('');
	let submitError = $state('');
	let scannerOpen = $state(false);
	let barcodeDescribedBy = $derived(
		submitError ? 'ticket-barcode-error ticket-barcode-hint' : 'ticket-barcode-hint'
	);

	function handleLinkTicket(event: SubmitEvent) {
		event.preventDefault();
		linkTicket();
	}

	function handleScanned(text: string) {
		barcode = text;
		linkTicket();
	}

	function linkTicket() {
		submitError = '';

		if (!barcode.trim()) {
			submitError = m.ticket_validation_required();
			return;
		}

		linkMutation.mutate(
			{ body: { barcode: barcode.trim() } },
			{
				onSuccess: () => {
					toastService.add(m.ticket_linked(), 'success');
					barcode = '';
				},
				onError: (error) => {
					submitError = getApiErrorDetail(error) ?? m.ticket_link_failed();
				}
			}
		);
	}
</script>

<SettingsSection description={m.ticket_link_description()}>
	{#if user.ticket}
		<div class="rounded-lg bg-success/10 p-4">
			<div class="flex items-center gap-2">
				<CircleCheck class="size-5 text-success" />
				<span class="font-medium text-success">{m.ticket_linked()}</span>
			</div>
			<p class="mt-2 text-sm text-success">
				{m.ticket_number_prefix()} <span class="font-mono font-medium">{user.ticket.barcode}</span>
			</p>
		</div>
	{:else}
		<form class="flex flex-col gap-3" onsubmit={offlineGate.guard(handleLinkTicket)}>
			<Field.Field data-invalid={submitError ? true : undefined}>
				<Field.FieldLabel for="ticket-barcode">{m.ticket_number_label()}</Field.FieldLabel>
				<Field.FieldDescription id="ticket-barcode-hint">
					{m.ticket_number_hint()}
				</Field.FieldDescription>
				<TicketNumberIllustration />
				<Input
					id="ticket-barcode"
					name="ticket_barcode"
					bind:value={barcode}
					autocomplete="off"
					autocapitalize="off"
					enterkeyhint="go"
					spellcheck={false}
					aria-invalid={submitError ? true : undefined}
					aria-describedby={barcodeDescribedBy}
					disabled={linkMutation.isPending}
					oninput={() => (submitError = '')}
				/>
				{#if submitError}
					<Field.FieldError id="ticket-barcode-error">{submitError}</Field.FieldError>
				{/if}
			</Field.Field>
			<Button
				type="submit"
				class="w-full"
				disabled={linkMutation.isPending}
				aria-disabled={offlineGate.blocked}
			>
				{#if linkMutation.isPending}
					<Spinner data-icon="inline-start" />
					{m.ticket_linking()}
				{:else}
					{m.ticket_link_action()}
				{/if}
			</Button>
			<Button
				type="button"
				variant="outline"
				class="w-full"
				disabled={linkMutation.isPending}
				aria-disabled={offlineGate.blocked}
				onclick={offlineGate.guard(() => (scannerOpen = true))}
			>
				<ScanLine data-icon="inline-start" />
				{m.ticket_scan_action()}
			</Button>
		</form>
		<BarcodeScannerDialog
			bind:open={scannerOpen}
			title={m.ticket_scan_title()}
			description={m.ticket_scan_description()}
			formats={TICKET_FORMATS}
			onDetect={handleScanned}
		/>
	{/if}
</SettingsSection>
