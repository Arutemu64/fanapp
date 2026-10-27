<script lang="ts">
	import type { Path } from '$app/types';
	import type { Component } from 'svelte';

	import Bell from '@lucide/svelte/icons/bell';
	import CalendarHeart from '@lucide/svelte/icons/calendar-heart';
	import Download from '@lucide/svelte/icons/download';
	import Ticket from '@lucide/svelte/icons/ticket';
	import UserPlus from '@lucide/svelte/icons/user-plus';

	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import MenuRow from '#lib/components/MenuRow.svelte';
	import { m } from '#lib/paraglide/messages.js';
	import { getPwaService } from '#lib/services/pwa.svelte.js';

	import type { ReadyStepKey } from './readySteps';

	interface Props {
		heading: string;
		steps: ReadyStepKey[];
	}

	let { heading, steps }: Props = $props();

	const pwa = getPwaService();

	interface ReadyStep {
		title: string;
		description: string;
		icon: Component;
		href?: Path;
		onclick?: () => void;
	}

	let installDescription = $derived(
		pwa.pushRequiresInstall ? m.install_description_ios() : m.install_description()
	);

	function stepFor(key: ReadyStepKey): ReadyStep {
		switch (key) {
			case 'account':
				return {
					title: m.ready_account_title(),
					description: m.ready_account_description(),
					icon: UserPlus,
					href: 'login'
				};
			case 'ticket':
				return {
					title: m.ticket_link_action(),
					description: m.ready_ticket_description(),
					icon: Ticket,
					href: 'profile/ticket'
				};
			case 'subscribe':
				return {
					title: m.ready_subscribe_title(),
					description: m.ready_subscribe_description(),
					icon: CalendarHeart,
					href: 'schedule'
				};
			case 'notifications':
				return {
					title: m.ready_notifications_title(),
					description: m.ready_notifications_description(),
					icon: Bell,
					href: 'profile/notifications'
				};
			case 'install':
				return {
					title: m.install_title(),
					description: installDescription,
					icon: Download,
					onclick: () => pwa.showInstallDialog()
				};
		}
	}
</script>

{#snippet stepRow(step: ReadyStep)}
	{#if step.href}
		<MenuRow
			href={step.href}
			label={step.title}
			description={step.description}
			fullDescription
			icon={step.icon}
			tone="primary"
		/>
	{:else if step.onclick}
		<MenuRow
			onclick={step.onclick}
			label={step.title}
			description={step.description}
			fullDescription
			icon={step.icon}
			tone="primary"
			chevron
		/>
	{/if}
{/snippet}

{#if steps.length > 0}
	<section aria-labelledby="get-ready-heading" class="flex flex-col gap-3">
		<h2 id="get-ready-heading" class="text-section text-foreground">
			{heading}
		</h2>

		<MenuGroup>
			{#each steps as key (key)}
				{@render stepRow(stepFor(key))}
			{/each}
		</MenuGroup>
	</section>
{/if}
