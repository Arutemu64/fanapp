<script lang="ts">
	import ClipboardCopy from '@lucide/svelte/icons/clipboard-copy';
	import { createMutation } from '@tanstack/svelte-query';

	import type { UserRole } from '#lib/api/generated/index.js';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import { generateTicketsMutation } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import FormError from '#lib/components/FormError.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { Textarea } from '#lib/components/ui/textarea/index.js';
	import { USER_ROLES } from '#lib/constants/users.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';
	import { getRoleLabel } from '#lib/utils/users.js';

	const toastService = getToastService();

	const MIN_AMOUNT = 1;
	const MAX_AMOUNT = 100;

	let selectedRole = $state<UserRole>('visitor');
	let selectedRoleLabel = $derived(getRoleLabel(selectedRole));
	// A `type="number"` binding yields a number, or an empty value when the field is
	// cleared — never a string. Validated as an integer in range on submit.
	let amountInput = $state<number | undefined>(10);
	const generateMutation = createMutation(() => generateTicketsMutation());

	let amountError = $state('');
	let submitError = $state('');

	let generatedBarcodes = $state<string[]>([]);
	// One barcode per line: pasting this into a spreadsheet fills a single column,
	// one ticket per row.
	let barcodesText = $derived(generatedBarcodes.join('\n'));

	function parseAmount(): number | null {
		// Guards both the cleared field (null/undefined) and non-integer input.
		if (!Number.isInteger(amountInput)) {
			return null;
		}
		return amountInput as number;
	}

	function validateAmount(): boolean {
		const parsed = parseAmount();
		if (parsed === null || parsed < MIN_AMOUNT || parsed > MAX_AMOUNT) {
			amountError = m.tickets_amount_validation({ min: MIN_AMOUNT, max: MAX_AMOUNT });
			return false;
		}
		amountError = '';
		return true;
	}

	function handleAmountInput() {
		if (amountError) {
			validateAmount();
		}
	}

	// A connection that drops mid-form keeps what was typed; the submit explains
	// itself instead of sending.
	const offlineGate = offlineWriteGate();

	function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';

		const amount = parseAmount();
		if (!validateAmount() || amount === null) {
			return;
		}

		generateMutation.mutate(
			{ body: { role: selectedRole, amount } },
			{
				onSuccess: (data) => {
					generatedBarcodes = data.barcodes;
					toastService.add(m.tickets_generated({ count: data.barcodes.length }), 'success');
				},
				onError: (error) => {
					const amountFieldError = getApiFieldError(error, 'amount');
					if (amountFieldError) {
						amountError = amountFieldError;
						return;
					}
					submitError = getApiErrorDetail(error) ?? m.tickets_generate_failed();
				}
			}
		);
	}

	async function copyBarcodes() {
		try {
			await navigator.clipboard.writeText(barcodesText);
			toastService.add(m.tickets_copied(), 'success');
		} catch (err) {
			console.error('Failed to copy barcodes:', err);
			toastService.add(m.tickets_copy_failed(), 'error');
		}
	}
</script>

<svelte:head>
	<title>{m.document_title({ title: m.tool_generate_tickets() })}</title>
</svelte:head>

<div class="mx-auto w-full max-w-2xl">
	<SectionIntro description={m.tickets_description()} />

	<form class="flex flex-col gap-6" onsubmit={offlineGate.guard(handleSubmit)}>
		<Field.FieldGroup class="gap-6">
			<Field.Field>
				<Field.FieldLabel for="ticket-role">{m.common_role()}</Field.FieldLabel>
				<Select.Root
					type="single"
					name="role"
					bind:value={selectedRole}
					disabled={generateMutation.isPending}
				>
					<Select.Trigger id="ticket-role" class="w-full">
						{selectedRoleLabel}
					</Select.Trigger>
					<Select.Content>
						<Select.Group>
							{#each USER_ROLES as role (role)}
								<Select.Item value={role} label={getRoleLabel(role)}>
									{getRoleLabel(role)}
								</Select.Item>
							{/each}
						</Select.Group>
					</Select.Content>
				</Select.Root>
				<Field.FieldDescription>{m.tickets_role_hint()}</Field.FieldDescription>
			</Field.Field>

			<Field.Field data-invalid={amountError ? true : undefined}>
				<Field.FieldLabel for="ticket-amount">{m.tickets_amount_label()}</Field.FieldLabel>
				<Input
					id="ticket-amount"
					type="number"
					min={MIN_AMOUNT}
					max={MAX_AMOUNT}
					step="1"
					bind:value={amountInput}
					disabled={generateMutation.isPending}
					oninput={handleAmountInput}
					aria-invalid={amountError ? true : undefined}
					class="w-full rounded-xl"
				/>
				{#if amountError}
					<Field.FieldError>{amountError}</Field.FieldError>
				{:else}
					<Field.FieldDescription>
						{m.tickets_amount_hint({ min: MIN_AMOUNT, max: MAX_AMOUNT })}
					</Field.FieldDescription>
				{/if}
			</Field.Field>
		</Field.FieldGroup>

		<FormError message={submitError} />

		<Button
			type="submit"
			class="w-full sm:w-auto"
			disabled={generateMutation.isPending}
			aria-disabled={offlineGate.blocked}
		>
			{#if generateMutation.isPending}
				<Spinner data-icon="inline-start" />
				{m.tickets_generating()}
			{:else}
				{m.tickets_generate_action()}
			{/if}
		</Button>
	</form>

	{#if generatedBarcodes.length > 0}
		<div class="mt-6 flex flex-col gap-3 border-t border-border pt-6">
			<div class="flex items-center justify-between gap-3">
				<span class="text-sm font-medium text-foreground">
					{m.tickets_ready({ count: generatedBarcodes.length })}
				</span>
				<Button type="button" variant="outline" size="sm" onclick={copyBarcodes}>
					<ClipboardCopy data-icon="inline-start" />
					{m.common_copy()}
				</Button>
			</div>
			<Textarea
				readonly
				rows={Math.min(generatedBarcodes.length, 10)}
				value={barcodesText}
				class="resize-none font-mono text-sm"
			/>
			<p class="text-xs text-muted-foreground">
				{m.tickets_copy_hint()}
			</p>
		</div>
	{/if}
</div>
