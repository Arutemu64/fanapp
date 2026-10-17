<script lang="ts">
	import { ShieldCheck } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type {
		CurrentUserDto,
		Permission,
		UserDetailsDto,
		UserRole
	} from '#lib/api/generated/index.js';

	import {
		getUserQueryKey,
		grantUserPermissionMutation,
		listUsersQueryKey,
		revokeUserPermissionMutation,
		setUserRoleMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import { Switch } from '#lib/components/ui/switch/index.js';
	import { USER_ROLES } from '#lib/constants/users.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import {
		canManagePermissions,
		canManageUsers,
		PERMISSION_LABELS
	} from '#lib/utils/permissions.js';
	import { getRoleLabel } from '#lib/utils/users.js';

	interface Props {
		profile: UserDetailsDto;
		currentUser: CurrentUserDto | null;
	}

	let { profile, currentUser }: Props = $props();

	const queryClient = useQueryClient();
	const toastService = getToastService();

	// The backend refuses changes to one's own access; the controls say so up
	// front instead of failing on tap.
	let isSelf = $derived(currentUser?.id === profile.id);
	let canEditRole = $derived(canManageUsers(currentUser) && !isSelf);
	let canEditPermissions = $derived(canManagePermissions(currentUser) && !isSelf);

	// "*" is granted from the server CLI only, so it never gets a switch.
	const ASSIGNABLE_PERMISSIONS = (Object.keys(PERMISSION_LABELS) as Permission[]).filter(
		(permission) => permission !== '*'
	);
	let hasWildcard = $derived(profile.permissions.includes('*'));
	let grantedLabels = $derived(
		profile.permissions.map((permission) => PERMISSION_LABELS[permission]())
	);

	function invalidateUser() {
		return Promise.all([
			queryClient.invalidateQueries({
				queryKey: getUserQueryKey({ path: { user_id: profile.id } })
			}),
			queryClient.invalidateQueries({ queryKey: listUsersQueryKey() })
		]);
	}

	let selectedRole = $state<UserRole | null>(null);
	let pickedRole = $derived(selectedRole ?? profile.role);

	const roleMutation = createMutation(() => ({
		...setUserRoleMutation(),
		onSuccess: invalidateUser
	}));

	function onRolePick(value: string) {
		selectedRole = USER_ROLES.find((role) => role === value) ?? null;
	}

	function saveRole() {
		const role = pickedRole;
		roleMutation.mutate(
			{ path: { user_id: profile.id }, body: { role } },
			{
				onSuccess: () => {
					selectedRole = null;
					toastService.add(m.role_changed({ role: getRoleLabel(role) }), 'success');
				},
				onError: (error) => toastService.error(error, m.role_change_failed())
			}
		);
	}

	const grantMutation = createMutation(() => ({
		...grantUserPermissionMutation(),
		onSuccess: invalidateUser
	}));
	const revokeMutation = createMutation(() => ({
		...revokeUserPermissionMutation(),
		onSuccess: invalidateUser
	}));

	// Switches toggle independently and their requests can overlap, so each call
	// awaits its own promise (mutate only runs the callbacks of the latest call).
	let pendingPermissions = $state<Permission[]>([]);

	async function setPermission(permission: Permission, granted: boolean) {
		const variables = { path: { user_id: profile.id, permission } };
		pendingPermissions = [...pendingPermissions, permission];
		try {
			if (granted) {
				await grantMutation.mutateAsync(variables);
			} else {
				await revokeMutation.mutateAsync(variables);
			}
		} catch (error) {
			toastService.error(error, m.permission_change_failed());
		} finally {
			pendingPermissions = pendingPermissions.filter((pending) => pending !== permission);
		}
	}
</script>

<Card.Root class="w-full max-w-none gap-4 p-4 sm:p-6">
	<div class="flex items-center gap-2">
		<ShieldCheck class="size-5 text-primary" aria-hidden="true" />
		<h2 class="text-section text-foreground">{m.access_title()}</h2>
	</div>

	{#if isSelf}
		<p class="text-sm text-muted-foreground">
			{m.access_self_note()}
		</p>
	{/if}

	<div class="flex flex-col gap-2">
		<h3 id="user-role-label" class="text-xs text-muted-foreground">{m.common_role()}</h3>
		{#if canEditRole}
			<div class="flex flex-col gap-2 sm:flex-row">
				<Select.Root
					type="single"
					value={pickedRole}
					onValueChange={onRolePick}
					disabled={roleMutation.isPending}
				>
					<Select.Trigger class="w-full sm:flex-1" aria-labelledby="user-role-label">
						{getRoleLabel(pickedRole)}
					</Select.Trigger>
					<Select.Content>
						{#each USER_ROLES as role (role)}
							<Select.Item value={role} label={getRoleLabel(role)}>{getRoleLabel(role)}</Select.Item
							>
						{/each}
					</Select.Content>
				</Select.Root>
				{#if pickedRole !== profile.role}
					<Button onclick={saveRole} disabled={roleMutation.isPending}
						>{m.access_save_role()}</Button
					>
				{/if}
			</div>
			<p class="text-xs text-muted-foreground">
				{m.access_role_hint()}
			</p>
		{:else}
			<div><Badge variant="secondary">{getRoleLabel(profile.role)}</Badge></div>
		{/if}
	</div>

	<div class="flex flex-col gap-2 border-t border-border pt-4">
		<h3 class="text-xs text-muted-foreground">{m.access_permissions_title()}</h3>
		{#if hasWildcard}
			<p class="text-sm text-foreground">{m.access_full_note()}</p>
		{/if}

		{#if canEditPermissions}
			<ul class="divide-y divide-border">
				{#each ASSIGNABLE_PERMISSIONS as permission (permission)}
					{const id = $derived(`permission-${permission.replace(':', '-')}`)}
					<li class="flex min-h-11 items-center justify-between gap-3 py-2">
						<label for={id} class="text-sm text-foreground">{PERMISSION_LABELS[permission]()}</label
						>
						<!-- Controlled: the switch shows the server's state, so a refused or
						     failed change never leaves it flipped. -->
						<Switch
							{id}
							bind:checked={
								() => profile.permissions.includes(permission),
								(granted: boolean) => void setPermission(permission, granted)
							}
							disabled={pendingPermissions.includes(permission)}
						/>
					</li>
				{/each}
			</ul>
		{:else if grantedLabels.length > 0 && !hasWildcard}
			<div class="flex flex-wrap gap-1.5">
				{#each grantedLabels as label (label)}
					<Badge variant="outline">{label}</Badge>
				{/each}
			</div>
		{:else if !hasWildcard}
			<p class="text-sm text-muted-foreground">{m.access_no_permissions()}</p>
		{/if}
	</div>
</Card.Root>
