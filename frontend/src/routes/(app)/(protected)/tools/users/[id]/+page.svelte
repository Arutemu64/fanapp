<script lang="ts">
	import BackLink from '$lib/components/BackLink.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import { Badge } from '$lib/components/ui/badge';
	import * as Card from '$lib/components/ui/card';
	import {
		buildSocialProfileUrl,
		getAvatarInitials,
		getRoleLabel,
		getSocialProviderLabel
	} from '$lib/utils/users';
	import { ExternalLink, Link2 } from '@lucide/svelte';

	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let profile = $derived(data.profile);
</script>

<svelte:head>
	<title>{profile.username} · ФАН ФАН</title>
</svelte:head>

<BackLink href="/tools/users" label="Назад к пользователям" />

<div class="mx-auto flex w-full max-w-2xl flex-col gap-5">
	<Card.Root class="flex w-full max-w-none flex-col gap-4 rounded-2xl p-4 sm:p-6">
		<div class="flex items-center gap-4">
			<span
				class="flex size-14 shrink-0 items-center justify-center rounded-full bg-primary/10 text-lg font-semibold text-primary"
				aria-hidden="true"
			>
				{getAvatarInitials(profile.username)}
			</span>
			<div class="min-w-0">
				<h1 class="truncate text-xl font-semibold text-foreground">
					{profile.username}
				</h1>
				<Badge variant="secondary" class="mt-1">
					{getRoleLabel(profile.role)}
				</Badge>
			</div>
		</div>

		<dl class="flex flex-col gap-3 border-t border-border pt-4 text-sm">
			<div class="flex flex-col gap-0.5">
				<dt class="text-xs text-muted-foreground">ID</dt>
				<dd class="font-mono text-xs break-all text-foreground select-all">
					{profile.id}
				</dd>
			</div>
			<div class="flex flex-col gap-0.5">
				<dt class="text-xs text-muted-foreground">Почта</dt>
				<dd class="break-all text-foreground">
					{profile.email ?? '—'}
				</dd>
			</div>
			<div class="flex flex-col gap-0.5">
				<dt class="text-xs text-muted-foreground">Номер билета</dt>
				<dd class="font-mono text-xs break-all text-foreground select-all">
					{profile.ticket_number ?? '—'}
				</dd>
			</div>
		</dl>
	</Card.Root>

	<Card.Root class="flex w-full max-w-none flex-col gap-4 rounded-2xl p-4 sm:p-6">
		<div class="flex items-center gap-2">
			<Link2 class="size-5 text-primary" aria-hidden="true" />
			<h2 class="text-lg font-semibold text-foreground">Привязанные аккаунты</h2>
		</div>

		{#if profile.social_links.length > 0}
			<ul class="flex flex-col gap-2">
				{#each profile.social_links as link (link.provider)}
					{@const url = buildSocialProfileUrl(link.provider, link.id)}
					<li class="flex items-center justify-between gap-3 rounded-xl border border-border p-3">
						<div class="min-w-0">
							<p class="text-sm font-medium text-foreground">
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
								class="inline-flex shrink-0 items-center gap-1 text-sm font-medium text-primary hover:underline"
							>
								Открыть
								<ExternalLink class="size-4" aria-hidden="true" />
							</a>
						{/if}
					</li>
				{/each}
			</ul>
		{:else}
			<EmptyState message="Нет привязанных аккаунтов." />
		{/if}
	</Card.Root>
</div>
