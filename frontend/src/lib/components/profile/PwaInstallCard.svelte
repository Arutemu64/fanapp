<script lang="ts">
	import { Button } from 'flowbite-svelte';
	import { DownloadSolid, ShareNodesOutline } from 'flowbite-svelte-icons';
	import { getPwaService } from '$lib/stores/pwa.svelte';
	import ProfileCardShell from './ProfileCardShell.svelte';

	const pwa = getPwaService();

	// Keep the helper visible on Android even when the browser only shows
	// installation through its own menu instead of `beforeinstallprompt`.
	let showCard = $derived(!pwa.isInstalled && (pwa.canInstall || pwa.isIOS || pwa.isAndroid));
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
		{:else if pwa.isAndroid}
			<div class="space-y-2">
				<div
					class="flex items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400"
				>
					<DownloadSolid class="h-5 w-5 shrink-0 text-gray-400" />
					<span>
						Откройте меню браузера и выберите «Установить приложение» или «Добавить на
						главный экран».
					</span>
				</div>

				{#if !pwa.isSecureContext}
					<p class="text-xs leading-5 text-gray-500 dark:text-gray-400">
						Если пункта нет, откройте сайт по HTTPS — Android не показывает установку на
						обычном HTTP.
					</p>
				{/if}
			</div>
		{/if}
	</ProfileCardShell>
{/if}
