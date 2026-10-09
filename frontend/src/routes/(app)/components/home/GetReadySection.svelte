<script lang="ts">
	import type { Path } from '$app/types';
	import type { Component } from 'svelte';

	import { resolve } from '$app/paths';
	import { Bell, CalendarHeart, ChevronRight, Download, Ticket, UserPlus } from '@lucide/svelte';

	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import * as Item from '#lib/components/ui/item/index.js';
	import { getPwaService } from '#lib/services/pwa.svelte.js';

	import type { ReadyStepKey } from './readySteps';

	interface Props {
		heading: string;
		/** The open steps, already decided by the page (see getReadySteps). */
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
		pwa.pushRequiresInstall
			? 'На iPhone и iPad уведомления приходят только в установленное приложение.'
			: 'Быстрый доступ с главного экрана и пуш-уведомления.'
	);

	function stepFor(key: ReadyStepKey): ReadyStep {
		switch (key) {
			case 'account':
				return {
					title: 'Создать аккаунт',
					description: 'Нужен для голосования и подписки на выступления программы.',
					icon: UserPlus,
					href: 'login'
				};
			case 'ticket':
				return {
					title: 'Привязать билет',
					description: 'Открывает доступ к голосованию в конкурсных номинациях.',
					icon: Ticket,
					href: 'profile/ticket'
				};
			case 'subscribe':
				return {
					title: 'Подписаться на выступления',
					description:
						'Отметь интересные номера в программе\u00A0— напомним, когда до них дойдёт очередь.',
					icon: CalendarHeart,
					href: 'schedule'
				};
			case 'notifications':
				return {
					title: 'Включить уведомления',
					description: 'Напоминания о выступлениях и новости фестиваля придут сразу на телефон.',
					icon: Bell,
					href: 'profile/notifications'
				};
			case 'install':
				return {
					title: 'Установить приложение',
					description: installDescription,
					icon: Download,
					// Open the install dialog directly; the library handles per-platform UX.
					onclick: () => pwa.showInstallDialog()
				};
		}
	}
</script>

{#snippet stepBody(step: ReadyStep)}
	<Item.Media class="size-9 rounded-lg bg-primary/10 text-primary">
		<step.icon class="size-5" aria-hidden="true" />
	</Item.Media>
	<Item.Content>
		<Item.Title class="text-base">{step.title}</Item.Title>
		<!-- Unclamped: the description is the reason to do the step, so it reads whole. -->
		<Item.Description class="line-clamp-none">{step.description}</Item.Description>
	</Item.Content>
	<Item.Actions>
		<ChevronRight class="size-4 text-muted-foreground" aria-hidden="true" />
	</Item.Actions>
{/snippet}

<!-- Every row is the same whole-row target, as in the profile hub: order and the
     counter carry priority, so no step gets a shape of its own. -->
{#snippet stepRow(step: ReadyStep)}
	<!-- hover:bg-muted by hand on the button: Item only highlights rows rendered as <a>. -->
	<Item.Root class="rounded-none hover:bg-muted">
		{#snippet child({ props })}
			{#if step.href}
				<a href={resolve(step.href)} {...props}>
					{@render stepBody(step)}
				</a>
			{:else}
				<button type="button" {...props} onclick={step.onclick}>
					{@render stepBody(step)}
				</button>
			{/if}
		{/snippet}
	</Item.Root>
{/snippet}

{#if steps.length > 0}
	<section aria-labelledby="get-ready-heading" class="flex flex-col gap-3">
		<h2 id="get-ready-heading" class="text-base font-semibold text-foreground sm:text-lg">
			{heading}
		</h2>

		<MenuGroup>
			{#each steps as key (key)}
				{@render stepRow(stepFor(key))}
			{/each}
		</MenuGroup>
	</section>
{/if}
