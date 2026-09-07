<script lang="ts">
	import type { components } from '$lib/api/schema';
	import type { CurrentUserDTO } from '$lib/types/user';

	import { PUBLIC_API_URL } from '$env/static/public';
	import { createApiClient } from '$lib/api';
	import * as Alert from '$lib/components/ui/alert';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import { SOCIAL_PROVIDER_PRESENTATION } from '$lib/data/socialProviders';
	import { getToastService } from '$lib/services/toasts.svelte';
	import { offlineWriteGate } from '$lib/utils/offlineAction';
	import { AlertCircle, Link, Mail, Shield } from '@lucide/svelte';

	import ChangeEmailModal from './ChangeEmailModal.svelte';
	import ChangePasswordModal from './ChangePasswordModal.svelte';
	import ProfileCardShell from './ProfileCardShell.svelte';
	import SocialConnectionRow from './SocialConnectionRow.svelte';

	type SocialProvider = components['schemas']['SocialProvider'];

	const client = createApiClient();

	interface Props {
		user: CurrentUserDTO;
		/** Providers this deployment offers for linking (see /auth/oauth/providers). */
		enabledProviders: SocialProvider[];
		onUpdate?: () => void | Promise<void>;
	}

	let { user, enabledProviders, onUpdate }: Props = $props();

	// Email/password/unlink are all mutations — online only. The current state
	// (which methods are set) still renders from the cached user.
	const offlineGate = offlineWriteGate();

	let changePasswordModalOpen = $state(false);
	let changeEmailModalOpen = $state(false);
	const toastService = getToastService();
	let emailStatusLabel = $derived(user.email ? 'Привязана' : 'Не добавлена');

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
	async function unlinkProvider(provider: SocialProvider) {
		const { name } = SOCIAL_PROVIDER_PRESENTATION[provider];
		try {
			const { error, response } =
				provider === 'vk'
					? await client.DELETE('/me/connections/vk', {})
					: await client.DELETE('/me/connections/telegram', {});

			if (error || !response.ok) {
				toastService.error(error);
				return;
			}

			toastService.add(`${name} отвязан`, 'success');
			await onUpdate?.();
		} catch (err) {
			toastService.error(err);
		}
	}
</script>

<ProfileCardShell
	title="Способы входа"
	description="Настрой почту, пароль и привязки для входа и восстановления доступа."
>
	{#snippet icon()}
		<Link class="size-5" />
	{/snippet}

	<!-- One bordered group with hairline dividers between rows, so related account
	     settings read as a set rather than as separate boxes-inside-a-box. -->
	<div class="divide-y divide-border overflow-hidden rounded-lg border border-border">
		<div class="p-3 sm:p-4">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div class="min-w-0">
					<div class="flex flex-wrap items-center gap-2">
						<Mail class="size-4 text-muted-foreground" />
						<p class="font-medium text-foreground">Эл. почта</p>
						<Badge variant={user.email ? 'default' : 'secondary'}>{emailStatusLabel}</Badge>
					</div>

					{#if user.email}
						<p class="mt-1.5 text-sm break-all text-muted-foreground">{user.email}</p>
					{:else}
						<p class="mt-1.5 text-sm leading-5 text-muted-foreground">
							Добавь email для восстановления доступа и важных уведомлений.
						</p>
					{/if}
				</div>

				<div class="flex w-full flex-col gap-2 sm:w-auto">
					<Button
						variant="outline"
						size="sm"
						class="min-h-11 w-full sm:w-auto"
						disabled={offlineGate.disabled}
						title={offlineGate.title}
						onclick={() => (changeEmailModalOpen = true)}
					>
						{user.email ? 'Изменить' : 'Добавить'}
					</Button>
				</div>
			</div>
		</div>

		<div class="p-3 sm:p-4">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div class="min-w-0">
					<div class="flex flex-wrap items-center gap-2">
						<Shield class="size-4 text-muted-foreground" />
						<p class="font-medium text-foreground">Пароль</p>
						<Badge variant={user.has_password ? 'default' : 'secondary'}>
							{user.has_password ? 'Установлен' : 'Не установлен'}
						</Badge>
					</div>

					<p class="mt-1.5 text-sm leading-5 text-muted-foreground">
						{#if user.has_password}
							Используй пароль как дополнительный способ входа.
						{:else}
							Установи пароль, чтобы входить без внешних сервисов.
						{/if}
					</p>
				</div>

				<Button
					variant="outline"
					size="sm"
					class="min-h-11 w-full sm:w-auto"
					disabled={offlineGate.disabled}
					title={offlineGate.title}
					onclick={() => (changePasswordModalOpen = true)}
				>
					{user.has_password ? 'Изменить' : 'Установить'}
				</Button>
			</div>
		</div>

		{#each connectionRows as provider (provider)}
			{@const meta = SOCIAL_PROVIDER_PRESENTATION[provider]}
			{@const Icon = meta.icon}
			<SocialConnectionRow
				label={meta.name}
				connected={linkedProviders.includes(provider)}
				connectedDescription={`Через ${meta.name} можно быстро входить без пароля.`}
				notConnectedDescription={`Подключи ${meta.name} для быстрого входа без пароля.`}
				connectHref={`${PUBLIC_API_URL}/me/connections/${provider}`}
				unlinkPrompt={`Отвязать ${meta.name}?`}
				hasEmail={Boolean(user.email)}
				onUnlink={() => unlinkProvider(provider)}
			>
				{#snippet icon()}
					<Icon class="size-4 text-muted-foreground" />
				{/snippet}
			</SocialConnectionRow>
		{/each}
	</div>

	{#if !user.email}
		<Alert.Root variant="warning">
			<AlertCircle />
			<Alert.Description>
				Добавь почту. Так будет проще восстановить доступ, и только после этого можно безопасно
				отвязать привязки.
			</Alert.Description>
		</Alert.Root>
	{/if}
</ProfileCardShell>

<ChangePasswordModal
	bind:open={changePasswordModalOpen}
	hasPassword={user.has_password}
	onSuccess={onUpdate}
/>

<ChangeEmailModal bind:open={changeEmailModalOpen} currentEmail={user.email} onSuccess={onUpdate} />
