<script lang="ts">
	import BackLink from '$lib/components/BackLink.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import {
		buildSocialProfileUrl,
		getAvatarInitials,
		getRoleColor,
		getRoleLabel,
		getSocialProviderLabel
	} from '$lib/utils/users';
	import { Badge, Card } from 'flowbite-svelte';
	import { ArrowUpRightFromSquareOutline, LinkOutline } from 'flowbite-svelte-icons';

	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let profile = $derived(data.profile);
</script>

<svelte:head>
	<title>{profile.username} · ФАН ФАН</title>
</svelte:head>

<BackLink href="/tools/users" label="Назад к пользователям" />

<div class="mx-auto w-full max-w-2xl space-y-5">
	<Card class="w-full max-w-none space-y-4 rounded-2xl p-4 sm:p-6">
		<div class="flex items-center gap-4">
			<span
				class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary-100 text-lg font-semibold text-primary-700 dark:bg-primary-900/40 dark:text-primary-300"
				aria-hidden="true"
			>
				{getAvatarInitials(profile.username)}
			</span>
			<div class="min-w-0">
				<h1 class="truncate text-xl font-semibold text-gray-900 dark:text-white">
					{profile.username}
				</h1>
				<Badge color={getRoleColor(profile.role)} class="mt-1">
					{getRoleLabel(profile.role)}
				</Badge>
			</div>
		</div>

		<dl class="space-y-3 border-t border-gray-100 pt-4 text-sm dark:border-gray-800">
			<div class="flex flex-col gap-0.5">
				<dt class="text-xs text-gray-500 dark:text-gray-400">ID</dt>
				<dd class="font-mono text-xs break-all text-gray-700 select-all dark:text-gray-300">
					{profile.id}
				</dd>
			</div>
			<div class="flex flex-col gap-0.5">
				<dt class="text-xs text-gray-500 dark:text-gray-400">Почта</dt>
				<dd class="break-all text-gray-700 dark:text-gray-300">
					{profile.email ?? '—'}
				</dd>
			</div>
			<div class="flex flex-col gap-0.5">
				<dt class="text-xs text-gray-500 dark:text-gray-400">Номер билета</dt>
				<dd class="font-mono text-xs break-all text-gray-700 select-all dark:text-gray-300">
					{profile.ticket_number ?? '—'}
				</dd>
			</div>
		</dl>
	</Card>

	<Card class="w-full max-w-none space-y-4 rounded-2xl p-4 sm:p-6">
		<div class="flex items-center gap-2">
			<LinkOutline class="h-5 w-5 text-primary-600 dark:text-primary-400" aria-hidden="true" />
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Привязанные аккаунты</h2>
		</div>

		{#if profile.social_links.length > 0}
			<ul class="space-y-2">
				{#each profile.social_links as link (link.provider)}
					{@const url = buildSocialProfileUrl(link.provider, link.id)}
					<li
						class="flex items-center justify-between gap-3 rounded-xl border border-gray-100 p-3 dark:border-gray-800"
					>
						<div class="min-w-0">
							<p class="text-sm font-medium text-gray-900 dark:text-white">
								{getSocialProviderLabel(link.provider)}
							</p>
							<p class="font-mono text-xs break-all text-gray-500 select-all dark:text-gray-400">
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
								class="inline-flex shrink-0 items-center gap-1 text-sm font-medium text-primary-600 hover:underline dark:text-primary-400"
							>
								Открыть
								<ArrowUpRightFromSquareOutline class="h-4 w-4" aria-hidden="true" />
							</a>
						{/if}
					</li>
				{/each}
			</ul>
		{:else}
			<EmptyState message="Нет привязанных аккаунтов." />
		{/if}
	</Card>
</div>
