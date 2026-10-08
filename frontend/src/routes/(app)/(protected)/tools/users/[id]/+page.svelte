<script lang="ts">
	import { ExternalLink } from '@lucide/svelte';

	import EmptyState from '#lib/components/EmptyState.svelte';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import SettingsSection from '#lib/components/SettingsSection.svelte';
	import * as Avatar from '#lib/components/ui/avatar/index.js';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import {
		buildSocialProfileUrl,
		getAvatarInitials,
		getRoleLabel,
		getSocialProviderLabel
	} from '#lib/utils/users.js';

	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let profile = $derived(data.profile);
</script>

<svelte:head>
	<title>{profile.username} · ФАН ФАН</title>
</svelte:head>

<!-- The same identity header and grouped rows as the user's own /profile/account,
     so an organiser reads a person's card in the shape they already know. The top
     bar already renders the username as the page <h1>. -->
<div class="flex flex-col gap-6">
	<div class="flex items-center gap-4">
		<Avatar.Root class="size-14 shrink-0 text-lg font-bold">
			<!-- primary-700 in light: on the primary/10 tint it clears AA, where
			     primary-600 doesn't (see ProfileHeader). -->
			<Avatar.Fallback class="bg-primary/10 text-primary-700 dark:text-primary">
				{getAvatarInitials(profile.username)}
			</Avatar.Fallback>
		</Avatar.Root>
		<div class="flex min-w-0 flex-col items-start gap-1">
			<p class="min-w-0 text-xl font-bold break-words text-foreground">
				@{profile.username}
			</p>
			<Badge variant="secondary" class="text-xs">
				{getRoleLabel(profile.role)}
			</Badge>
		</div>
	</div>

	<SettingsSection title="Данные">
		<MenuGroup>
			<dl class="divide-y divide-border text-sm">
				<div class="flex flex-col gap-0.5 p-4">
					<dt class="text-xs text-muted-foreground">Почта</dt>
					<dd class="break-all text-foreground">{profile.email ?? '—'}</dd>
				</div>
				<div class="flex flex-col gap-0.5 p-4">
					<dt class="text-xs text-muted-foreground">Номер билета</dt>
					<dd class="font-mono break-all text-foreground select-all">
						{profile.ticket_number ?? '—'}
					</dd>
				</div>
				<div class="flex flex-col gap-0.5 p-4">
					<dt class="text-xs text-muted-foreground">ID</dt>
					<dd class="font-mono text-xs break-all text-foreground select-all">{profile.id}</dd>
				</div>
			</dl>
		</MenuGroup>
	</SettingsSection>

	<SettingsSection title="Привязанные аккаунты">
		{#if profile.social_links.length > 0}
			<MenuGroup>
				<ul class="divide-y divide-border">
					{#each profile.social_links as link (link.provider)}
						{@const url = buildSocialProfileUrl(link.provider, link.id)}
						<li class="flex items-center justify-between gap-3 p-4">
							<div class="min-w-0">
								<p class="text-base font-medium text-foreground">
									{getSocialProviderLabel(link.provider)}
								</p>
								<p class="font-mono text-xs break-all text-muted-foreground select-all">
									{link.id}
								</p>
							</div>
							{#if url}
								<!-- rel="external": account deep link (vk.com / tg://), not an
								     internal route — resolve() is only for app pathnames. -->
								<a
									href={url}
									target="_blank"
									rel="external noopener noreferrer"
									class="inline-flex min-h-11 shrink-0 items-center gap-1 text-sm font-medium text-primary hover:underline"
								>
									Открыть
									<ExternalLink class="size-4" aria-hidden="true" />
								</a>
							{/if}
						</li>
					{/each}
				</ul>
			</MenuGroup>
		{:else}
			<EmptyState message="Нет привязанных аккаунтов." />
		{/if}
	</SettingsSection>
</div>
