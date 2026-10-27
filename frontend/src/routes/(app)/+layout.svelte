<script lang="ts">
	import {
		type AfterNavigate,
		afterNavigate,
		beforeNavigate,
		type OnNavigate,
		onNavigate
	} from '$app/navigation';
	import { page } from '$app/state';
	import { createQuery } from '@tanstack/svelte-query';
	import { prefersReducedMotion } from 'svelte/motion';
	import { MediaQuery } from 'svelte/reactivity';

	import SkipLink from '#lib/components/SkipLink.svelte';
	import { DESKTOP_MEDIA_QUERY } from '#lib/constants/layout.js';
	import { TAB_ROOTS } from '#lib/data/nav.js';
	import { currentUserOptions } from '#lib/services/identity.js';
	import { resolvePath } from '#lib/utils/paths.js';

	import type { LayoutProps } from './$types';

	import AppBottomNav from './components/AppBottomNav.svelte';
	import AppNavbar from './components/AppNavbar.svelte';
	import AppSidebar from './components/AppSidebar.svelte';
	import ConnectionBanner from './components/ConnectionBanner.svelte';
	import { navTransitionKind } from './navTransition';

	let { children }: LayoutProps = $props();

	let activeUrl = $derived(page.url.pathname);
	const userQuery = createQuery(() => currentUserOptions());
	let user = $derived(userQuery.data ?? null);

	let userId = $derived(user?.id ?? null);
	let tabMemory = $derived.by(() => {
		// eslint-disable-next-line @typescript-eslint/no-unused-expressions -- read only to reset on an account change
		userId;
		const lastSearches = $state<Record<string, string>>({});
		const scrollTops: Record<string, number> = {};
		return { lastSearches, scrollTops };
	});

	let scrollBehavior: ScrollBehavior = $derived(
		prefersReducedMotion.current ? 'instant' : 'smooth'
	);

	function scrollPageToTop() {
		window.scrollTo({ top: 0, behavior: scrollBehavior });
		revealNavbar();
	}

	const SCROLL_DELTA_PX = 6;
	let navbarHidden = $state(false);
	let contentScrolled = $state(false);
	let navbarHeight = $state(0);
	let chromeHeight = $state(0);
	let lastScrollTop = 0;
	let scrollFrame = 0;

	const isDesktop = new MediaQuery(DESKTOP_MEDIA_QUERY);
	let chromeHidden = $derived(navbarHidden && !isDesktop.current);

	let chromeTransitionMs = $derived(chromeHidden ? 200 : 300);
	let chromeEasing = $derived(
		chromeHidden ? 'cubic-bezier(0.3, 0, 0.8, 0.15)' : 'cubic-bezier(0.05, 0.7, 0.1, 1)'
	);

	let stickyTop = $derived(chromeHidden ? chromeHeight - navbarHeight : chromeHeight);

	$effect(() => {
		const root = document.documentElement;
		root.style.scrollPaddingTop = `${chromeHeight}px`;
		root.style.scrollPaddingBottom = isDesktop.current
			? ''
			: 'calc(var(--bottom-nav-clearance) + var(--bottom-accessory-clearance))';
		return () => {
			root.style.removeProperty('scroll-padding-top');
			root.style.removeProperty('scroll-padding-bottom');
		};
	});

	function revealNavbar() {
		navbarHidden = false;
		lastScrollTop = window.scrollY;
	}

	function syncChromeToScroll() {
		revealNavbar();
		contentScrolled = window.scrollY > 0;
	}

	function handleScroll() {
		if (scrollFrame) return;
		scrollFrame = requestAnimationFrame(() => {
			scrollFrame = 0;
			const top = window.scrollY;
			contentScrolled = top > 0;
			const maxTop = document.documentElement.scrollHeight - window.innerHeight;
			if (top < 0 || top > maxTop) return;
			const delta = top - lastScrollTop;
			if (Math.abs(delta) < SCROLL_DELTA_PX) return;
			navbarHidden = delta > 0 && top > navbarHeight;
			lastScrollTop = top;
		});
	}

	beforeNavigate((navigation) => {
		if (navigation.shallow) return;
		const from = navigation.from?.url.pathname;
		if (from && TAB_ROOTS.has(from)) {
			tabMemory.scrollTops[from] = window.scrollY;
		}
	});

	afterNavigate((navigation) => {
		if (navigation.shallow) return;
		const to = navigation.to?.url.pathname ?? '';
		if (TAB_ROOTS.has(to)) {
			tabMemory.lastSearches[to] = navigation.to?.url.search ?? '';
		}
		if (isQueryOnlyNavigation(navigation, to)) return;
		if (navigation.type !== 'popstate') restoreTabScroll(to);
		syncChromeToScroll();
	});

	function isQueryOnlyNavigation(navigation: AfterNavigate, to: string): boolean {
		return (
			navigation.type !== 'enter' &&
			navigation.type !== 'popstate' &&
			navigation.from?.url.pathname === to
		);
	}

	function restoreTabScroll(to: string) {
		const savedTop = tabMemory.scrollTops[to];
		if (TAB_ROOTS.has(to) && savedTop !== undefined && savedTop > 0) {
			window.scrollTo({ top: savedTop, behavior: 'instant' });
		}
	}

	let transitionId = 0;

	function canAnimateNavigation(navigation: OnNavigate): boolean {
		if (!('startViewTransition' in document)) return false;
		if (isDesktop.current || prefersReducedMotion.current) return false;
		return navigation.to?.route.id?.startsWith('/(app)') ?? false;
	}

	onNavigate((navigation) => {
		if (navigation.shallow || !canAnimateNavigation(navigation)) return;
		if (!navigation.from || !navigation.to) return;

		const kind = navTransitionKind({
			from: navigation.from.url.pathname,
			to: navigation.to.url.pathname,
			fromBackHref: page.data.back && resolvePath(page.data.back.href),
			tabRoots: TAB_ROOTS
		});
		if (!kind) return;

		const id = ++transitionId;
		const root = document.documentElement;
		root.dataset.navTransition = kind;

		return new Promise<void>((resolve) => {
			const transition = document.startViewTransition(async () => {
				resolve();
				await navigation.complete;
			});
			transition.ready.catch(() => {});
			transition.updateCallbackDone.catch(() => {});
			transition.finished
				.catch(() => {})
				.finally(() => {
					if (id === transitionId) delete root.dataset.navTransition;
				});
		});
	});
</script>

<svelte:window onscroll={handleScroll} />

<div
	class="flex min-h-dvh w-full bg-background pr-[env(safe-area-inset-right)] pl-[env(safe-area-inset-left)]"
>
	<SkipLink />

	<AppSidebar
		{activeUrl}
		avatarSeed={user?.avatar_seed ?? null}
		lastSearches={tabMemory.lastSearches}
		scrollToTop={scrollPageToTop}
	/>

	<div class="relative flex min-w-0 flex-1 flex-col overflow-x-clip">
		<div
			bind:offsetHeight={chromeHeight}
			onfocusin={revealNavbar}
			class="sticky z-(--z-chrome) backdrop-blur-md transition-[top] [view-transition-name:top-chrome] motion-reduce:transition-none reduced-transparency:bg-background reduced-transparency:backdrop-blur-none"
			style:top={chromeHidden ? `-${navbarHeight}px` : '0px'}
			style:transition-duration={`${chromeTransitionMs}ms`}
			style:transition-timing-function={chromeEasing}
		>
			<div bind:offsetHeight={navbarHeight}>
				<AppNavbar {user} {contentScrolled} lastSearches={tabMemory.lastSearches} />
			</div>
			<ConnectionBanner />
		</div>

		<main
			id="main-content"
			tabindex="-1"
			style:--sticky-top={`${stickyTop}px`}
			style:--sticky-top-duration={`${chromeTransitionMs}ms`}
			style:--sticky-top-easing={chromeEasing}
			class="flex flex-1 flex-col focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
		>
			<div
				class="mx-auto w-full max-w-5xl grow p-4 pb-[calc(var(--bottom-nav-clearance)+1rem)] has-[>[data-fill-column]]:flex has-[>[data-fill-column]]:flex-col md:p-6 md:pt-4 lg:p-8 lg:pt-4"
			>
				{@render children()}
			</div>
		</main>
	</div>

	<AppBottomNav
		{activeUrl}
		avatarSeed={user?.avatar_seed ?? null}
		lastSearches={tabMemory.lastSearches}
		scrollToTop={scrollPageToTop}
	/>
</div>
