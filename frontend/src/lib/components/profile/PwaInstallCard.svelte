<script lang="ts">
	import { Button } from 'flowbite-svelte';
	import { DownloadSolid, ShareNodesOutline } from 'flowbite-svelte-icons';
	import { getPwaService } from '$lib/stores/pwa.svelte';
	import ProfileCardShell from './ProfileCardShell.svelte';

	const pwa = getPwaService();

	let showCard = $derived(!pwa.isInstalled && (pwa.canInstall || pwa.isIOS));
</script>

{#if showCard}
	<ProfileCardShell
		title="Установить приложение"
		description="Добавьте FAN FAN на главный экран, чтобы быстрее открывать профиль и уведомления."
	>
		{#snippet icon()}
			<DownloadSolid class="h-5 w-5 text-primary-600 dark:text-primary-300" />
		{/snippet}

		{#if pwa.canInstall}
			<Button color="primary" class="min-h-11 w-full sm:w-auto" onclick={() => pwa.install()}>
				<DownloadSolid class="me-2 h-5 w-5" />
				Установить
			</Button>
		{:else if pwa.isIOS}
			<div
				class="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400"
			>
				<ShareNodesOutline class="h-5 w-5 shrink-0 text-gray-400" />
				<span>Нажмите «Поделиться», затем «На экран „Домой“».</span>
			</div>
		{/if}
	</ProfileCardShell>
{/if}
