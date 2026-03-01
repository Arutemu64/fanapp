<script lang="ts">
	import { Card, Button } from 'flowbite-svelte';
	import { DownloadSolid, ShareNodesOutline } from 'flowbite-svelte-icons';
	import { getPwaService } from '$lib/stores/pwa.svelte';

	const pwa = getPwaService();

	let showCard = $derived(!pwa.isInstalled && (pwa.canInstall || pwa.isIOS));
</script>

{#if showCard}
	<Card class="w-full max-w-none rounded-lg bg-white shadow dark:bg-gray-800">
		<div class="p-6">
			<div class="flex items-center gap-4">
				<div
					class="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900"
				>
					<DownloadSolid class="h-6 w-6 text-primary-600 dark:text-primary-300" />
				</div>
				<div class="flex-1">
					<h3 class="text-lg font-bold text-gray-900 dark:text-white">Установить приложение</h3>
					<p class="text-sm leading-relaxed text-gray-500 dark:text-gray-400">
						Установите FAN FAN на главный экран для быстрого доступа ко всем функциям.
					</p>
				</div>
			</div>

			{#if pwa.canInstall}
				<Button color="primary" class="mt-4 w-full" size="lg" onclick={() => pwa.install()}>
					<DownloadSolid class="mr-2 h-5 w-5" />
					Установить
				</Button>
			{:else if pwa.isIOS}
				<div
					class="mt-4 flex items-center gap-3 rounded-lg bg-gray-50 p-3 text-sm text-gray-600 dark:bg-gray-800 dark:text-gray-400"
				>
					<ShareNodesOutline class="h-5 w-5 shrink-0 text-gray-400" />
					<span> Нажмите «Поделиться», затем «На экран „Домой“» </span>
				</div>
			{/if}
		</div>
	</Card>
{/if}
