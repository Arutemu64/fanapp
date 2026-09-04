<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { getPwaService } from '$lib/services/pwa.svelte';
	import { Download } from '@lucide/svelte';

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
			<Download class="size-5" />
		{/snippet}

		<Button class="min-h-11 w-full sm:w-auto" onclick={() => pwa.showInstallDialog()}>
			<Download data-icon="inline-start" />
			Установить
		</Button>
	</ProfileCardShell>
{/if}
