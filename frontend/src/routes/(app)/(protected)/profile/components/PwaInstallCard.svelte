<script lang="ts">
	import { Button } from 'flowbite-svelte';
	import { DownloadSolid } from 'flowbite-svelte-icons';
	import { getPwaService } from '$lib/services/pwa.svelte';
	import ProfileCardShell from './ProfileCardShell.svelte';

	const pwa = getPwaService();
</script>

<!--
	The install button opens the @khmyznikov/pwa-install dialog, which renders its
	own platform-specific instructions (Chromium prompt, iOS "На экран Домой", etc.).
-->
{#if pwa.canInstall}
	<ProfileCardShell
		title="Установить приложение"
		description="Добавь ФАН ФАН на главный экран, чтобы быстрее открывать приложение и получать пуш-уведомления."
	>
		{#snippet icon()}
			<DownloadSolid class="h-5 w-5" />
		{/snippet}

		<Button
			color="primary"
			class="min-h-11 w-full sm:w-auto"
			onclick={() => pwa.showInstallDialog()}
		>
			<DownloadSolid class="me-2 h-5 w-5" />
			Установить
		</Button>
	</ProfileCardShell>
{/if}
