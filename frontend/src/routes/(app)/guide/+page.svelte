<script lang="ts">
	import type { Component } from 'svelte';

	import {
		ExternalLink,
		Globe,
		Mail,
		Map as MapIcon,
		MapPin,
		MessageCircle,
		ScrollText
	} from '@lucide/svelte';
	import { createQuery } from '@tanstack/svelte-query';
	import IconTelegram from '~icons/simple-icons/telegram';
	import IconVk from '~icons/simple-icons/vk';

	import { getPublicConfigOptions } from '#lib/api/generated/@tanstack/svelte-query.gen.js';
	import logo from '#lib/assets/logo.svg';
	import MenuGroup from '#lib/components/MenuGroup.svelte';
	import MenuLink from '#lib/components/MenuLink.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Item from '#lib/components/ui/item/index.js';
	import { FALLBACK_CONFIG } from '#lib/constants/festival.js';
	import { guideArticles } from '#lib/data/guideArticles.js';
	import { m } from '#lib/paraglide/messages.js';
	import { formatFestivalDate, formatFestivalTime } from '#lib/utils/formatters.js';

	// A text search, so there are no coordinates to keep in step with the venue.
	// https://yandex.com/dev/yandex-apps-launch-maps/doc/en/concepts/yandexmaps-web
	const yandexMapsUrl = `https://yandex.ru/maps/?text=${encodeURIComponent('Нижний Новгород, ДК ГАЗ')}`;

	interface SocialLink {
		href: string;
		label: () => string;
		icon: Component;
		/** mailto: stays in the app's tab; web links open elsewhere. */
		external: boolean;
	}

	const socialLinks: SocialLink[] = [
		{ href: 'https://fancom.info/', label: m.guide_website, icon: Globe, external: true },
		{ href: 'https://vk.com/ffest_nn', label: m.guide_vk, icon: IconVk, external: true },
		{
			href: 'https://t.me/fanfan_fest_news',
			label: m.guide_telegram,
			icon: IconTelegram,
			external: true
		},
		{ href: 'https://max.ru/ffest_nn', label: m.guide_max, icon: MessageCircle, external: true },
		{ href: 'mailto:orgcom.fan@mail.ru', label: m.guide_email, icon: Mail, external: false }
	];

	// The date and start come from the public config organizers edit, the same source
	// as Home, so the two tabs can't disagree; the cached copy or the shipped
	// defaults fill in offline. Doors and the age limit aren't in the config.
	const configQuery = createQuery(() => getPublicConfigOptions());
	const config = $derived(configQuery.data ?? FALLBACK_CONFIG);
	const facts = $derived([
		formatFestivalDate(config.festival_start),
		m.guide_doors(),
		m.guide_start({ time: formatFestivalTime(config.festival_start) }),
		m.guide_age()
	]);
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

<!-- A hub, like /profile: the intro with the facts and social links, then grouped
     rows that each lead somewhere. Grouped rows with a trailing indicator are the
     phone-settings shape for "drill in"
     (https://developer.apple.com/design/human-interface-guidelines/lists-and-tables),
     so every target is a full-width tap. Capped and centred like the profile column. -->
<div class="mx-auto flex w-full max-w-2xl flex-col gap-4 sm:gap-5">
	<section aria-labelledby="guide-heading" class="rounded-2xl border bg-card p-5 sm:p-6">
		<img src={logo} alt={m.app_name()} class="h-10 w-auto dark:invert" />
		<h2 id="guide-heading" class="mt-4 text-lg leading-snug font-semibold text-balance">
			{m.guide_tagline()}
		</h2>
		<p class="mt-1.5 text-sm leading-relaxed text-muted-foreground">{m.guide_about()}</p>
		<ul class="mt-3 flex flex-wrap gap-2">
			{#each facts as fact (fact)}
				<li class="rounded-full bg-muted px-3 py-1 text-sm font-medium">{fact}</li>
			{/each}
		</ul>
		<ul class="mt-4 flex flex-wrap gap-2">
			{#each socialLinks as link (link.href)}
				{@const Icon = link.icon}
				<li>
					<Button
						variant="outline"
						size="icon"
						href={link.href}
						target={link.external ? '_blank' : undefined}
						rel={link.external ? 'noopener noreferrer' : undefined}
					>
						<Icon aria-hidden="true" />
						<span class="sr-only">
							{link.label()}{link.external ? ` (${m.guide_opens_in_new_tab()})` : ''}
						</span>
					</Button>
				</li>
			{/each}
		</ul>
	</section>

	<section aria-labelledby="guide-important" class="flex flex-col gap-2">
		<h2 id="guide-important" class="px-1 text-sm font-medium text-muted-foreground">
			{m.guide_important_heading()}
		</h2>
		<MenuGroup>
			<MenuLink href="guide/map" label={m.nav_map()} icon={MapIcon} />
			{@render externalRow(
				yandexMapsUrl,
				MapPin,
				`${m.guide_venue_name()}, ${m.guide_venue_address()}`,
				m.guide_open_in_yandex_maps()
			)}
			{@render externalRow(
				'https://fancom.info/pages/rules',
				ScrollText,
				m.guide_rules(),
				'fancom.info/pages/rules'
			)}
		</MenuGroup>
	</section>

	<section aria-labelledby="guide-activities" class="flex flex-col gap-2">
		<h2 id="guide-activities" class="px-1 text-sm font-medium text-muted-foreground">
			{m.guide_activities_heading()}
		</h2>
		<MenuGroup>
			{#each guideArticles as article (article.slug)}
				<MenuLink
					href={`guide/${article.slug}`}
					label={article.title}
					description={article.description}
					icon={article.icon}
				/>
			{/each}
		</MenuGroup>
	</section>
</div>
