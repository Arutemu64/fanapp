<script lang="ts">
	import { PUBLIC_API_URL } from '$app/env/public';
	import { Mail, Shield } from '@lucide/svelte';
	import { createMutation, useQueryClient } from '@tanstack/svelte-query';

	import type { CurrentUserDto, SocialProvider } from '#lib/api/generated/index.js';

	import {
		getCurrentUserQueryKey,
		unlinkTelegramAccountMutation,
		unlinkVkAccountMutation
	} from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Item from '#lib/components/ui/item/index.js';
	import { SOCIAL_PROVIDER_PRESENTATION } from '#lib/data/socialProviders.js';
	import { m } from '#lib/paraglide/messages.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { offlineWriteGate } from '#lib/utils/offlineAction.js';

	import ChangeEmailModal from './ChangeEmailModal.svelte';
	import ChangePasswordModal from './ChangePasswordModal.svelte';
	import SettingsSection from './SettingsSection.svelte';
	import SocialConnectionRow from './SocialConnectionRow.svelte';

	interface Props {
		user: CurrentUserDto;
		/** Providers this deployment offers for linking (see /auth/oauth/providers). */
		enabledProviders: SocialProvider[];
	}

	let { user, enabledProviders }: Props = $props();
	const queryClient = useQueryClient();

	// Email/password/unlink are all mutations — online only. The current state
	// (which methods are set) still renders from the cached user.
	const offlineGate = offlineWriteGate();

	let changePasswordModalOpen = $state(false);
	let changeEmailModalOpen = $state(false);
	const toastService = getToastService();
	// Each row's second line is its current state, not a description of the setting
	// (Android settings guidance: "Secondary text below the setting label reflects
	// the current selection"), so a phone shows the whole group without scrolling.
	let emailStatus = $derived(user.email ?? m.sign_in_email_missing());
	let passwordStatus = $derived(
		user.has_password ? m.sign_in_password_set() : m.sign_in_password_unset()
	);
	// Colour goes to the action the user is missing, not to a state that is fine
	// (DESIGN.md "Color-Earns-Its-Place"): a missing email is the one to fix.
	let emailButtonVariant = $derived<'outline' | 'default'>(user.email ? 'outline' : 'default');

	let linkedProviders = $derived(user.social_identities.map((si) => si.provider));

	// Rows are the enabled providers (in the backend's display order) plus any the
	// user already linked that are no longer enabled — those must stay visible so a
	// linked account can always be unlinked, even after its provider is turned off.
	// A non-enabled row is therefore always connected, so it shows unlink and no
	// connect; SocialConnectionRow needs no notion of "enabled" for that to hold.
	let connectionRows = $derived([
		...enabledProviders,
		...linkedProviders.filter((provider) => !enabledProviders.includes(provider))
	]);

	// SocialConnectionRow owns the confirm-and-loading UI and calls this to perform
	// the unlink. The DELETE path is per-provider (ADR-0012's distinct routes), so a
	// literal is picked here rather than an interpolated path the typed client can't
	// check. Unlink is never gated by enablement — that is what keeps a disabled-but-
	// linked provider removable.
	const unlinkVkMutation = createMutation(() => ({
		...unlinkVkAccountMutation(),
		onSuccess: refreshUser
	}));
	const unlinkTelegramMutation = createMutation(() => ({
		...unlinkTelegramAccountMutation(),
		onSuccess: refreshUser
	}));

	// Connections ship with the current user, so its query is the one to refresh.
	function refreshUser() {
		return queryClient.invalidateQueries({ queryKey: getCurrentUserQueryKey() });
	}

	// `mutateAsync`, not `mutate`: SocialConnectionRow awaits this to drive its
	// confirm strip and spinner.
	async function unlinkProvider(provider: SocialProvider) {
		const { name } = SOCIAL_PROVIDER_PRESENTATION[provider];
		const unlinkMutation = provider === 'vk' ? unlinkVkMutation : unlinkTelegramMutation;

		try {
			await unlinkMutation.mutateAsync({});
		} catch (error) {
			toastService.error(error);
			return;
		}
		toastService.add(m.sign_in_unlinked({ name }), 'success');
	}
</script>

<SettingsSection title={m.sign_in_title()} description={m.sign_in_description()}>
	<!-- One bordered group with hairline dividers between rows, so related account
	     settings read as a set rather than as separate boxes. -->
	<MenuGroup class="divide-y divide-border">
		<Item.Root class="rounded-none">
			<Item.Media class="size-9 rounded-lg bg-muted text-muted-foreground">
				<Mail class="size-5" aria-hidden="true" />
			</Item.Media>
			<Item.Content class="min-w-0">
				<Item.Title class="text-base">{m.sign_in_email()}</Item.Title>
				<Item.Description class="line-clamp-none wrap-anywhere">{emailStatus}</Item.Description>
			</Item.Content>
			<Item.Actions>
				<Button
					variant={emailButtonVariant}
					size="sm"
					class="min-h-11"
					aria-disabled={offlineGate.blocked}
					onclick={offlineGate.guard(() => (changeEmailModalOpen = true))}
				>
					{user.email ? m.common_change() : m.common_add()}
				</Button>
			</Item.Actions>
		</Item.Root>

		<Item.Root class="rounded-none">
			<Item.Media class="size-9 rounded-lg bg-muted text-muted-foreground">
				<Shield class="size-5" aria-hidden="true" />
			</Item.Media>
			<Item.Content class="min-w-0">
				<Item.Title class="text-base">{m.sign_in_password()}</Item.Title>
				<Item.Description>{passwordStatus}</Item.Description>
			</Item.Content>
			<Item.Actions>
				<Button
					variant="outline"
					size="sm"
					class="min-h-11"
					aria-disabled={offlineGate.blocked}
					onclick={offlineGate.guard(() => (changePasswordModalOpen = true))}
				>
					{user.has_password ? m.common_change() : m.common_set()}
				</Button>
			</Item.Actions>
		</Item.Root>

		{#each connectionRows as provider (provider)}
			{@const meta = SOCIAL_PROVIDER_PRESENTATION[provider]}
			{@const Icon = meta.icon}
			<SocialConnectionRow
				label={meta.name}
				connected={linkedProviders.includes(provider)}
				connectHref={`${PUBLIC_API_URL}/me/connections/${provider}`}
				unlinkPrompt={m.sign_in_unlink_prompt({ name: meta.name })}
				hasEmail={Boolean(user.email)}
				onUnlink={() => unlinkProvider(provider)}
			>
				{#snippet icon()}
					<Icon class="size-5" aria-hidden="true" />
				{/snippet}
			</SocialConnectionRow>
		{/each}
	</MenuGroup>
</SettingsSection>

<ChangePasswordModal bind:open={changePasswordModalOpen} hasPassword={user.has_password} />

<ChangeEmailModal bind:open={changeEmailModalOpen} currentEmail={user.email} />
