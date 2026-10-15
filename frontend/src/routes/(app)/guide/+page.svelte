<script lang="ts">
	import type { Component } from 'svelte';

	import { ExternalLink, Globe, Map as MapIcon, MapPin } from '@lucide/svelte';
	import IconTelegram from '~icons/simple-icons/telegram';
	import IconVk from '~icons/simple-icons/vk';

	import logo from '#lib/assets/logo.svg';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import MenuLink from '#lib/components/MenuLink.svelte';
	import * as Item from '#lib/components/ui/item/index.js';
	import { m } from '#lib/paraglide/messages.js';

	// A text search, so there are no coordinates to keep in step with the venue.
	// https://yandex.com/dev/yandex-apps-launch-maps/doc/en/concepts/yandexmaps-web
	const yandexMapsUrl = `https://yandex.ru/maps/?text=${encodeURIComponent('Нижний Новгород, ДК ГАЗ')}`;

	interface ContactLink {
		href: string;
		label: () => string;
		/** The bare address, so people know where the row leads before leaving the app. */
		hint: string;
		icon: Component;
	}

	const contacts: ContactLink[] = [
		{ href: 'https://fancom.info/', label: m.guide_website, hint: 'fancom.info', icon: Globe },
		{ href: 'https://vk.com/ffest_nn', label: m.guide_vk, hint: 'vk.com/ffest_nn', icon: IconVk },
		{
			href: 'https://t.me/fanfan_fest_news',
			label: m.guide_telegram,
			hint: 't.me/fanfan_fest_news',
			icon: IconTelegram
		}
	];
</script>

<svelte:head>
	<title>{m.document_title({ title: m.nav_guide() })}</title>
</svelte:head>

{#snippet externalRow(href: string, Icon: Component, title: string, description: string)}
	<Item.Root class="rounded-none">
		{#snippet child({ props })}
			<a {href} target="_blank" rel="noopener noreferrer" {...props}>
				<Item.Media class="size-9 rounded-lg bg-muted text-muted-foreground">
					<Icon class="size-5" aria-hidden="true" />
				</Item.Media>
				<Item.Content>
					<Item.Title class="text-base">{title}</Item.Title>
					<Item.Description>{description}</Item.Description>
				</Item.Content>
				<Item.Actions>
					<ExternalLink class="size-4 text-muted-foreground" aria-hidden="true" />
					<span class="sr-only">({m.guide_opens_in_new_tab()})</span>
				</Item.Actions>
			</a>
		{/snippet}
	</Item.Root>
{/snippet}

<!-- A hub, like /profile: an intro, then grouped rows that each lead somewhere —
     the map one level down, directions and contacts out to other apps. Grouped
     rows with a trailing indicator are the phone-settings shape for "drill in"
     (https://developer.apple.com/design/human-interface-guidelines/lists-and-tables),
     so the page reads at a glance and every target is a full-width tap. Capped
     and centred for the same reason as the profile column. -->
<div class="mx-auto flex w-full max-w-2xl flex-col gap-4 sm:gap-5">
	<section aria-labelledby="guide-heading" class="rounded-2xl border bg-card p-5 sm:p-6">
		<img src={logo} alt={m.app_name()} class="h-10 w-auto dark:invert" />
		<h2 id="guide-heading" class="mt-4 text-lg leading-snug font-semibold text-balance">
			{m.guide_tagline()}
		</h2>
		<p class="mt-2 text-muted-foreground">{m.guide_about()}</p>
	</section>

	<MenuGroup>
		<MenuLink href="guide/map" label={m.nav_map()} icon={MapIcon} />
	</MenuGroup>

	<section aria-labelledby="guide-directions" class="flex flex-col gap-2">
		<h2 id="guide-directions" class="px-1 text-sm font-medium text-muted-foreground">
			{m.guide_directions_heading()}
		</h2>
		<MenuGroup>
			{@render externalRow(
				yandexMapsUrl,
				MapPin,
				`${m.guide_venue_name()}, ${m.guide_venue_address()}`,
				m.guide_open_in_yandex_maps()
			)}
		</MenuGroup>
	</section>

	<section aria-labelledby="guide-contacts" class="flex flex-col gap-2">
		<h2 id="guide-contacts" class="px-1 text-sm font-medium text-muted-foreground">
			{m.guide_contacts_heading()}
		</h2>
		<MenuGroup>
			{#each contacts as contact (contact.href)}
				{@render externalRow(contact.href, contact.icon, contact.label(), contact.hint)}
			{/each}
		</MenuGroup>
	</section>
</div>
