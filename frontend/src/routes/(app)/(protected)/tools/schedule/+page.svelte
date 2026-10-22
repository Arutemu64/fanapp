<script lang="ts">
	import SectionIntro from '#lib/components/SectionIntro.svelte';
	import * as Tabs from '#lib/components/ui/tabs/index.js';
	import { m } from '#lib/paraglide/messages.js';

	import type { PageProps } from './$types';

	import ToolSection from '../components/ToolSection.svelte';
	import ImportScheduleForm from './components/ImportScheduleForm.svelte';
	import ScheduleTimingsForm from './components/ScheduleTimingsForm.svelte';

	let { data }: PageProps = $props();
</script>

<svelte:head>
	<title>{m.document_title({ title: m.nav_schedule() })}</title>
</svelte:head>

<div class="mx-auto flex w-full max-w-2xl flex-col gap-4">
	<SectionIntro description={m.tool_schedule_intro()} />

	<Tabs.Root value="import" class="gap-4">
		<Tabs.List aria-label={m.schedule_tool_tabs_label()} class="w-full sm:w-auto">
			<Tabs.Trigger value="import">{m.schedule_tool_tab_import()}</Tabs.Trigger>
			<Tabs.Trigger value="timings">{m.schedule_tool_tab_timings()}</Tabs.Trigger>
		</Tabs.List>

		<Tabs.Content value="import">
			<ImportScheduleForm />
		</Tabs.Content>

		<Tabs.Content value="timings">
			<ToolSection>
				<ScheduleTimingsForm initial={data.timings} />
			</ToolSection>
		</Tabs.Content>
	</Tabs.Root>
</div>
