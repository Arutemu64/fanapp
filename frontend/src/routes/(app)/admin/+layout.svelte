<script lang="ts">
	import AppShell from '$lib/components/layout/AppShell.svelte';

	let { data, children } = $props();

	// Keep admin navigation short and task-oriented on all admin pages.
	const sidebarItems = [
		{ label: 'Админ-панель', href: '/admin' },
		{ label: 'Выйти из админки', href: '/' }
	];
</script>

<AppShell {data} {children} {sidebarItems} showBottomNav={false} contentBottomPaddingClass="pb-6" />
