<script lang="ts">
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { UserRole } from '#lib/api/generated/index.js';

	import { getApiErrorCode, getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import {
		listBroadcastsQueryKey,
		sendBroadcastMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import FormError from '#lib/components/FormError.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Checkbox } from '#lib/components/ui/checkbox/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { Textarea } from '#lib/components/ui/textarea/index.js';
	import { BROADCAST_BODY_MAX_LENGTH } from '#lib/constants/notifications.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';
	import { uuidv7 } from '#lib/utils/uuidv7.js';

	import BroadcastHistory from './components/BroadcastHistory.svelte';

	const toastService = getToastService();
	const queryClient = useQueryClient();

	const broadcastMutation = createMutation(() => ({
		...sendBroadcastMutation(),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: listBroadcastsQueryKey() })
	}));

	// One ID per broadcast, kept across submits: if a send's response is lost,
	// pressing again replays it on the server instead of mailing everyone twice
	// (docs/adr/0034). A fresh one is drawn only once this broadcast is settled.
	let mailingId = uuidv7();

	let bodyText = $state('');
	let selectedRoles = $state<UserRole[]>([]);

	let charsLeft = $derived(BROADCAST_BODY_MAX_LENGTH - bodyText.length);

	let bodyError = $state('');
	let rolesError = $state('');
	let submitError = $state('');

	function validateForm() {
		let isValid = true;

		if (!bodyText.trim()) {
			bodyError = m.broadcast_validation_text();
			isValid = false;
		} else {
			bodyError = '';
		}

		if (selectedRoles.length === 0) {
			rolesError = m.broadcast_validation_roles();
			isValid = false;
		} else {
			rolesError = '';
		}

		return isValid;
	}

	function handleBodyInput() {
		if (bodyError) {
			bodyError = bodyText.trim() ? '' : m.broadcast_validation_text();
		}
	}

	function handleRoleChange() {
		if (rolesError) {
			rolesError = selectedRoles.length > 0 ? '' : m.broadcast_validation_roles();
		}
	}

	function toggleRole(role: UserRole, checked: boolean) {
		if (checked) {
			if (!selectedRoles.includes(role)) selectedRoles = [...selectedRoles, role];
		} else {
			selectedRoles = selectedRoles.filter((r) => r !== role);
		}
		handleRoleChange();
	}

	// A connection that drops mid-form keeps what was typed; the submit explains
	// itself instead of sending.
	const offlineGate = offlineWriteGate();

	function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';

		if (!validateForm()) {
			return;
		}

		broadcastMutation.mutate(
			{
				body: {
					mailing_id: mailingId,
					body: bodyText.trim(),
					roles: selectedRoles
				}
			},
			{
				onSuccess: () => {
					mailingId = uuidv7();
					toastService.add(m.broadcast_started(), 'success');
					bodyText = '';
					selectedRoles = [];
					bodyError = '';
					rolesError = '';
				},
				onError: (error) => {
					bodyError = getApiFieldError(error, 'body') ?? '';
					rolesError = getApiFieldError(error, 'roles') ?? '';
					if (bodyError || rolesError) {
						return;
					}
					// An earlier press went through but its response was lost, and the
					// text changed since. That broadcast is out; the next press sends
					// the edited text as a new one.
					if (getApiErrorCode(error) === 'MAILING_ALREADY_EXISTS') {
						mailingId = uuidv7();
						void queryClient.invalidateQueries({ queryKey: listBroadcastsQueryKey() });
					}
					submitError = getApiErrorDetail(error) ?? m.broadcast_start_failed();
				}
			}
		);
	}
</script>

<svelte:head>
	<title>{m.document_title({ title: m.tool_broadcast() })}</title>
</svelte:head>

<div class="mx-auto w-full max-w-2xl">
	<SectionIntro description={m.broadcast_description()} />

	<form class="flex flex-col gap-6" onsubmit={offlineGate.guard(handleSubmit)}>
		<Field.Field data-invalid={bodyError ? true : undefined}>
			<Field.FieldLabel for="broadcast-body">{m.broadcast_text_label()}</Field.FieldLabel>
			<Textarea
				id="broadcast-body"
				name="body"
				rows={4}
				maxlength={BROADCAST_BODY_MAX_LENGTH}
				placeholder={m.broadcast_text_placeholder()}
				bind:value={bodyText}
				disabled={broadcastMutation.isPending}
				oninput={handleBodyInput}
				class="resize-none"
				aria-invalid={bodyError ? true : undefined}
			/>
			{#if bodyError}
				<Field.FieldError>{bodyError}</Field.FieldError>
			{:else}
				<Field.FieldDescription>
					{m.broadcast_text_hint()}
				</Field.FieldDescription>
				<Field.FieldDescription>
					{m.broadcast_chars_left({ count: charsLeft })}
				</Field.FieldDescription>
			{/if}
		</Field.Field>

		<Field.FieldSet data-invalid={rolesError ? true : undefined}>
			<Field.FieldLegend variant="label">{m.broadcast_roles_label()}</Field.FieldLegend>
			<Field.FieldGroup data-slot="checkbox-group" class="grid grid-cols-1 gap-3 sm:grid-cols-2">
				<Field.Field orientation="horizontal">
					<Checkbox
						id="role-visitor"
						checked={selectedRoles.includes('visitor')}
						onCheckedChange={(v) => toggleRole('visitor', v === true)}
						disabled={broadcastMutation.isPending}
					/>
					<Field.FieldLabel for="role-visitor" class="cursor-pointer font-normal">
						{m.audience_visitors()}
					</Field.FieldLabel>
				</Field.Field>
				<Field.Field orientation="horizontal">
					<Checkbox
						id="role-participant"
						checked={selectedRoles.includes('participant')}
						onCheckedChange={(v) => toggleRole('participant', v === true)}
						disabled={broadcastMutation.isPending}
					/>
					<Field.FieldLabel for="role-participant" class="cursor-pointer font-normal">
						{m.audience_participants()}
					</Field.FieldLabel>
				</Field.Field>
				<Field.Field orientation="horizontal">
					<Checkbox
						id="role-volunteer"
						checked={selectedRoles.includes('volunteer')}
						onCheckedChange={(v) => toggleRole('volunteer', v === true)}
						disabled={broadcastMutation.isPending}
					/>
					<Field.FieldLabel for="role-volunteer" class="cursor-pointer font-normal">
						{m.audience_volunteers()}
					</Field.FieldLabel>
				</Field.Field>
				<Field.Field orientation="horizontal">
					<Checkbox
						id="role-organizer"
						checked={selectedRoles.includes('organizer')}
						onCheckedChange={(v) => toggleRole('organizer', v === true)}
						disabled={broadcastMutation.isPending}
					/>
					<Field.FieldLabel for="role-organizer" class="cursor-pointer font-normal">
						{m.audience_organizers()}
					</Field.FieldLabel>
				</Field.Field>
			</Field.FieldGroup>
			{#if rolesError}
				<Field.FieldError>{rolesError}</Field.FieldError>
			{/if}
		</Field.FieldSet>

		<FormError message={submitError} />

		<Button
			type="submit"
			class="w-full sm:w-auto"
			disabled={broadcastMutation.isPending}
			aria-disabled={offlineGate.blocked}
		>
			{#if broadcastMutation.isPending}
				<Spinner data-icon="inline-start" />
				{m.common_sending()}
			{:else}
				{m.broadcast_submit()}
			{/if}
		</Button>
	</form>
</div>

<div class="mt-8">
	<BroadcastHistory />
</div>
