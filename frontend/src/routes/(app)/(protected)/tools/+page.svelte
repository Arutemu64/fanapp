<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';

	import { getPublicConfigOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import { requirePublicConfig } from '#lib/api/index.js';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import { toolsFor } from '#lib/data/tools.js';
	import { m } from '#lib/paraglide/messages.js';
	import { isOrganizer } from '#lib/utils/permissions.js';

	import type { PageProps } from './$types';

	import OnlineNowCard from './components/OnlineNowCard.svelte';
	import ToolRow from './components/ToolRow.svelte';

	let { data }: PageProps = $props();
	// The (protected) guard's snapshot: these rows only gate links.
	let user = $derived(data.user);
	let organizer = $derived(isOrganizer(user));

	const configQuery = createQuery(() => getPublicConfigOptions());

	let tools = $derived(toolsFor(user, requirePublicConfig(configQuery.data)));
</script>

<!-- Capped and centred like the /profile hub this menu continues. -->
<div class="mx-auto max-w-2xl">
	<SectionIntro description={m.tools_intro()} />

	<!-- Shown to every organizer, with no per-tool permission scoping the live count;
	     volunteers come here for their own tools only. -->
	{#if organizer}
		<div class="mb-4">
			<OnlineNowCard />
		</div>
	{/if}

	<MenuGroup>
		{#each tools as tool (tool.key)}
			<ToolRow
				title={tool.title}
				description={tool.description}
				icon={tool.icon}
				href={tool.href}
			/>
		{/each}
	</MenuGroup>
</div>
