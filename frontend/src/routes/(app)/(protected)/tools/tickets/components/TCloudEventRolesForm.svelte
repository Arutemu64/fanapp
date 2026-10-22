<script lang="ts">
	import Plus from '@lucide/svelte/icons/plus';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';
	import { untrack } from 'svelte';

	import type { TCloudEventRolesOutput, UserRole } from '#lib/api/generated/index.js';

	import { getApiErrorDetail } from '#lib/api/errors.js';
	import {
		getTcloudEventRolesQueryKey,
		setTcloudEventRolesMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import FormError from '#lib/components/FormError.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import { USER_ROLES } from '#lib/constants/users.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';
	import { getRoleLabel } from '#lib/utils/users.js';

	interface Props {
		/** The saved mapping; the form is seeded from it once. */
		initial: TCloudEventRolesOutput;
	}

	let { initial }: Props = $props();

	const toastService = getToastService();
	const queryClient = useQueryClient();

	interface Row {
		// A stable {#each} key, so removing a row keeps focus and input state on
		// the rows that stay.
		key: number;
		eventId: string;
		role: UserRole;
		error: string;
	}

	let nextKey = 0;

	function newRow(eventId: string, role: UserRole): Row {
		nextKey += 1;
		return { key: nextKey, eventId, role, error: '' };
	}

	function snapshot(list: Row[]): string {
		return JSON.stringify(list.map((row) => [row.eventId.trim(), row.role]));
	}

	let rows = $state<Row[]>(
		untrack(() => initial.event_roles.map((item) => newRow(item.event_id, item.role)))
	);
	let savedSnapshot = $state(untrack(() => snapshot(rows)));
	let hasChanges = $derived(snapshot(rows) !== savedSnapshot);
	let submitError = $state('');

	const saveMutation = createMutation(() => ({
		...setTcloudEventRolesMutation(),
		onSuccess: () => queryClient.invalidateQueries({ queryKey: getTcloudEventRolesQueryKey() })
	}));

	function addRow() {
		rows.push(newRow('', 'participant'));
	}

	function removeRow(key: number) {
		rows = rows.filter((row) => row.key !== key);
	}

	function validate(): boolean {
		const seen: string[] = [];
		let valid = true;
		for (const row of rows) {
			const eventId = row.eventId.trim();
			row.error = '';
			if (!eventId) {
				row.error = m.tcloud_roles_validation_required();
			} else if (seen.includes(eventId)) {
				row.error = m.tcloud_roles_validation_duplicate();
			}
			if (row.error) {
				valid = false;
			}
			seen.push(eventId);
		}
		return valid;
	}

	// A connection that drops mid-form keeps what was typed; the submit explains
	// itself instead of sending.
	const offlineGate = offlineWriteGate();

	function handleSubmit(event: Event) {
		event.preventDefault();
		submitError = '';
		if (!validate()) {
			return;
		}
		const eventRoles = rows.map((row) => ({ event_id: row.eventId.trim(), role: row.role }));
		saveMutation.mutate(
			{ body: { event_roles: eventRoles } },
			{
				onSuccess: () => {
					savedSnapshot = snapshot(rows);
					toastService.add(m.tcloud_roles_saved(), 'success');
				},
				onError: (error) => {
					submitError = getApiErrorDetail(error) ?? m.settings_save_failed();
				}
			}
		);
	}
</script>

<form novalidate class="flex flex-col gap-4" onsubmit={offlineGate.guard(handleSubmit)}>
	<p class="text-sm text-muted-foreground">{m.tcloud_roles_description()}</p>

	{#if rows.length === 0}
		<p class="text-sm text-muted-foreground">{m.tcloud_roles_empty()}</p>
	{/if}

	{#each rows as row, index (row.key)}
		<div class="flex items-start gap-2">
			<Field.Field data-invalid={row.error ? true : undefined} class="min-w-0 flex-1">
				<Field.FieldLabel for="tcloud-event-{row.key}" class="sr-only">
					{m.tcloud_roles_event_label({ number: index + 1 })}
				</Field.FieldLabel>
				<Input
					id="tcloud-event-{row.key}"
					autocomplete="off"
					autocapitalize="off"
					spellcheck={false}
					placeholder={m.tcloud_roles_event_placeholder()}
					class="font-mono"
					bind:value={row.eventId}
					disabled={saveMutation.isPending}
					oninput={() => (row.error = '')}
					aria-invalid={row.error ? true : undefined}
				/>
				{#if row.error}
					<Field.FieldError>{row.error}</Field.FieldError>
				{/if}
			</Field.Field>
			<Select.Root type="single" bind:value={row.role} disabled={saveMutation.isPending}>
				<Select.Trigger
					class="w-36 shrink-0"
					aria-label={m.tcloud_roles_role_label({ number: index + 1 })}
				>
					{getRoleLabel(row.role)}
				</Select.Trigger>
				<Select.Content>
					{#each USER_ROLES as role (role)}
						<Select.Item value={role} label={getRoleLabel(role)}>{getRoleLabel(role)}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
			<Button
				type="button"
				variant="ghost"
				size="icon"
				class="shrink-0"
				aria-label={m.tcloud_roles_remove({ number: index + 1 })}
				disabled={saveMutation.isPending}
				onclick={() => removeRow(row.key)}
			>
				<Trash2 aria-hidden="true" />
			</Button>
		</div>
	{/each}

	<Button
		type="button"
		variant="outline"
		class="w-full sm:w-auto sm:self-start"
		disabled={saveMutation.isPending}
		onclick={addRow}
	>
		<Plus data-icon="inline-start" />
		{m.tcloud_roles_add()}
	</Button>

	<FormError message={submitError} />

	<Button
		type="submit"
		class="w-full sm:w-auto sm:self-start"
		disabled={saveMutation.isPending || !hasChanges}
		aria-disabled={offlineGate.blocked}
	>
		{#if saveMutation.isPending}
			<Spinner data-icon="inline-start" />
			{m.common_saving()}
		{:else}
			{m.common_save()}
		{/if}
	</Button>
</form>
