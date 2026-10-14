<script lang="ts">
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import { getApiErrorDetail, getApiFieldError } from '#lib/api/errors.js';
	import {
		listBroadcastsQueryKey,
		sendBroadcastMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Checkbox } from '#lib/components/ui/checkbox/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { Textarea } from '#lib/components/ui/textarea/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	import BroadcastHistory from './components/BroadcastHistory.svelte';

	const toastService = getToastService();
	const queryClient = useQueryClient();

	const broadcastMutation = createMutation(() => ({
		...sendBroadcastMutation(),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: listBroadcastsQueryKey() })
	}));

	let bodyText = $state('');
	let selectedRoles = $state<string[]>([]);

	let bodyError = $state('');
	let rolesError = $state('');
	let submitError = $state('');

	function validateForm() {
		let isValid = true;

		if (!bodyText.trim()) {
			bodyError = m.broadcast_body_required();
			isValid = false;
		} else {
			bodyError = '';
		}

		if (selectedRoles.length === 0) {
			rolesError = m.broadcast_roles_required();
			isValid = false;
		} else {
			rolesError = '';
		}

		return isValid;
	}

	function handleBodyInput() {
		if (bodyError) {
			bodyError = bodyText.trim() ? '' : m.broadcast_body_required();
		}
	}

	function handleRoleChange() {
		if (rolesError) {
			rolesError = selectedRoles.length > 0 ? '' : m.broadcast_roles_required();
		}
	}

	function toggleRole(role: string, checked: boolean) {
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
					body: bodyText.trim(),
					roles: selectedRoles as ('visitor' | 'participant' | 'helper' | 'org')[]
				}
			},
			{
				onSuccess: () => {
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
					submitError = getApiErrorDetail(error) ?? m.broadcast_start_failed();
				}
			}
		);
	}
</script>

<svelte:head>
	<title>{m.tool_broadcast_title()} · {m.brand_name()}</title>
</svelte:head>

<div class="mx-auto w-full max-w-2xl">
	<SectionIntro description={m.broadcast_description()} />

	<form class="flex flex-col gap-6" onsubmit={offlineGate.guard(handleSubmit)}>
		<Field.Field data-invalid={bodyError ? true : undefined}>
			<Field.FieldLabel for="broadcast-body">{m.broadcast_body_label()}</Field.FieldLabel>
			<Textarea
				id="broadcast-body"
				name="body"
				rows={4}
				placeholder={m.broadcast_body_placeholder()}
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
					{m.broadcast_body_hint()}
				</Field.FieldDescription>
			{/if}
		</Field.Field>

		<Field.FieldSet data-invalid={rolesError ? true : undefined}>
			<Field.FieldLegend variant="label">{m.broadcast_recipients()}</Field.FieldLegend>
			<Field.FieldGroup data-slot="checkbox-group" class="grid grid-cols-1 gap-3 sm:grid-cols-2">
				<Field.Field orientation="horizontal">
					<Checkbox
						id="role-visitor"
						checked={selectedRoles.includes('visitor')}
						onCheckedChange={(v) => toggleRole('visitor', !!v)}
						disabled={broadcastMutation.isPending}
					/>
					<Field.FieldLabel for="role-visitor" class="cursor-pointer font-normal">
						{m.role_visitors()}
					</Field.FieldLabel>
				</Field.Field>
				<Field.Field orientation="horizontal">
					<Checkbox
						id="role-participant"
						checked={selectedRoles.includes('participant')}
						onCheckedChange={(v) => toggleRole('participant', !!v)}
						disabled={broadcastMutation.isPending}
					/>
					<Field.FieldLabel for="role-participant" class="cursor-pointer font-normal">
						{m.role_participants()}
					</Field.FieldLabel>
				</Field.Field>
				<Field.Field orientation="horizontal">
					<Checkbox
						id="role-helper"
						checked={selectedRoles.includes('helper')}
						onCheckedChange={(v) => toggleRole('helper', !!v)}
						disabled={broadcastMutation.isPending}
					/>
					<Field.FieldLabel for="role-helper" class="cursor-pointer font-normal">
						{m.role_helpers()}
					</Field.FieldLabel>
				</Field.Field>
				<Field.Field orientation="horizontal">
					<Checkbox
						id="role-org"
						checked={selectedRoles.includes('org')}
						onCheckedChange={(v) => toggleRole('org', !!v)}
						disabled={broadcastMutation.isPending}
					/>
					<Field.FieldLabel for="role-org" class="cursor-pointer font-normal">
						{m.role_orgs()}
					</Field.FieldLabel>
				</Field.Field>
			</Field.FieldGroup>
			{#if rolesError}
				<Field.FieldError>{rolesError}</Field.FieldError>
			{/if}
		</Field.FieldSet>

		{#if submitError}
			<Alert.Root variant="destructive">
				<Alert.Description>{submitError}</Alert.Description>
			</Alert.Root>
		{/if}

		<Button
			type="submit"
			class="w-full sm:w-auto"
			disabled={broadcastMutation.isPending}
			aria-disabled={offlineGate.blocked}
		>
			{#if broadcastMutation.isPending}
				<Spinner data-icon="inline-start" />
				{m.broadcast_sending()}
			{:else}
				{m.broadcast_send()}
			{/if}
		</Button>
	</form>
</div>

<div class="mt-8">
	<BroadcastHistory />
</div>
