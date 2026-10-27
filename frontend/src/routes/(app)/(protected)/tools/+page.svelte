<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	import { getPublicConfigOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import MenuRow from '#lib/components/MenuRow.svelte';
	import OfflineUnavailableState from '#lib/components/OfflineUnavailableState.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { FALLBACK_CONFIG } from '#lib/constants/festival.js';
	import { toolsFor } from '#lib/data/tools.js';
	import { m } from '#lib/paraglide/messages.js';
	import { reachability } from '#lib/services/reachability.js';

	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	let user = $derived(data.user);

	const configQuery = createQuery(() => getPublicConfigOptions());

	let tools = $derived(toolsFor(user, configQuery.data ?? FALLBACK_CONFIG));
	let offline = $derived(data.offlineUnavailable && !reachability.current);
	let shownTools = $derived(offline ? tools.filter((tool) => tool.worksOffline) : tools);
</script>

{#if offline && shownTools.length === 0}
	<OfflineUnavailableState />
{:else}
	<div class="mx-auto max-w-2xl">
		<SectionIntro description={m.tools_intro()} />

		<MenuGroup>
			{#each shownTools as tool (tool.key)}
				<MenuRow
					href={tool.href}
					label={tool.title}
					description={tool.description}
					icon={tool.icon}
				/>
			{/each}
		</MenuGroup>
	</div>
{/if}
