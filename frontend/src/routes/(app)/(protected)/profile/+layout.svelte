<script lang="ts">
	import BackLink from '$lib/components/BackLink.svelte';
	import StaleDataNotice from '$lib/components/StaleDataNotice.svelte';
	import { getOfflineService } from '$lib/services/offline.svelte';

	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	// Every profile sub-page renders from the layout-cached user, so the only "out of
	// date" state is being offline.
	const offline = getOfflineService();
	let showStaleNotice = $derived(!offline.isOnline);
	const staleNoticeMessage = 'Нет связи. Показан сохранённый профиль — обновится при подключении.';
</script>

<!-- The /profile hub itself lives outside (protected) so guests can open it; only
     these settings pages behind it need an account. -->
<!-- Same centred column as the /profile hub, so the back link and the cards stay
     where the hub's rows were. -->
<div class="mx-auto max-w-2xl">
	<BackLink href="/profile" label="Назад в профиль" />

	<div class="flex flex-col gap-4 sm:gap-5">
		{#if showStaleNotice}
			<StaleDataNotice message={staleNoticeMessage} />
		{/if}

		{@render children()}
	</div>
</div>
