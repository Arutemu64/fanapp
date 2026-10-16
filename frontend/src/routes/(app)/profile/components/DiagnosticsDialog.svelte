<script lang="ts">
	import { Copy, RotateCcw, Stethoscope } from '@lucide/svelte';
	import { type QueryClient, useQueryClient } from '@tanstack/svelte-query';
	import { del } from 'idb-keyval';
	import { untrack } from 'svelte';

	import type { CurrentUserDto } from '#lib/api/generated/index.js';

	import { checkSubscription } from '#lib/api/generated/index.js';
	import { QUERY_CACHE_KEY } from '#lib/api/queryPersister.js';
	import * as AlertDialog from '#lib/components/ui/alert-dialog/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { m } from '#lib/paraglide/messages.js';
	import { browserPush } from '#lib/services/pushBrowser.js';
	import { getPwaService } from '#lib/services/pwa.svelte.js';
	import { reachability } from '#lib/services/reachability.js';
	import { getToastService } from '#lib/services/toasts.svelte.js';
	import { FIRST_PAINT_TIMEOUT_MS, timeoutSignal } from '#lib/utils/fetchTimeout.js';
	import { getRoleLabel } from '#lib/utils/users.js';

	import {
		buildSections,
		CACHE_LABELS,
		type CacheEntry,
		type DiagnosticsSnapshot,
		formatReport,
		type PushDiagnostics,
		type ServiceWorkerStatus,
		type StorageDiagnostics
	} from '../diagnostics.js';

	interface Props {
		open: boolean;
		user: CurrentUserDto | null;
		version: string;
		build: string;
	}

	let { open = $bindable(false), user, version, build }: Props = $props();

	const queryClient = useQueryClient();
	const pwa = getPwaService();
	const toastService = getToastService();

	let snapshot = $state.raw<DiagnosticsSnapshot | null>(null);
	let capturedAt = $state(0);
	let sections = $derived(snapshot ? buildSections(snapshot, capturedAt) : []);
	let confirmResetOpen = $state(false);
	let isResetting = $state(false);

	// Gathered on open rather than kept live: it is a snapshot for a report, and
	// reading it once keeps the Push and Storage API calls off the profile screen.
	// Untracked so only `open` re-runs it, not the reachability it records.
	$effect(() => {
		if (open) untrack(() => void refresh());
	});

	async function refresh() {
		const [serviceWorker, push, storage] = await Promise.all([
			readServiceWorker(),
			readPush(),
			readStorage()
		]);
		capturedAt = Date.now();
		snapshot = {
			version,
			build,
			account: user ? `@${user.username} · ${getRoleLabel(user.role)}` : null,
			installed: pwa.isInstalled,
			userAgent: navigator.userAgent,
			serverReachable: reachability.current,
			deviceOnline: reachability.deviceOnline,
			serviceWorker,
			push,
			storage,
			cache: readCache(queryClient)
		};
	}

	async function readServiceWorker(): Promise<ServiceWorkerStatus> {
		if (!('serviceWorker' in navigator)) return 'unsupported';
		const registration = await navigator.serviceWorker.getRegistration().catch(() => undefined);
		if (!registration) return 'none';
		if (registration.waiting) return 'update-waiting';
		if (registration.active) return 'active';
		return 'installing';
	}

	async function readPush(): Promise<PushDiagnostics> {
		if (!browserPush.isSupported()) {
			return {
				permission: 'unsupported',
				subscribed: false,
				pushService: null,
				serverRegistered: null
			};
		}
		const subscription = await browserPush.getSubscription().catch(() => null);
		let serverRegistered: boolean | null = null;
		// Only a signed-in user has subscriptions on the server, and offline the
		// question can't be asked.
		if (subscription && user && reachability.current) {
			// Bounded so a stalled request can't hold back the rest of the report,
			// which is all local; a timeout leaves the answer unknown.
			const { data } = await checkSubscription({
				query: { endpoint: subscription.endpoint },
				signal: timeoutSignal(FIRST_PAINT_TIMEOUT_MS)
			});
			serverRegistered = data?.subscribed ?? null;
		}
		return {
			permission: browserPush.permission(),
			subscribed: subscription !== null,
			pushService: subscription ? new URL(subscription.endpoint).host : null,
			serverRegistered
		};
	}

	// https://developer.mozilla.org/en-US/docs/Web/API/StorageManager/estimate
	async function readStorage(): Promise<StorageDiagnostics> {
		const storage = navigator.storage as Partial<StorageManager> | undefined;
		const [estimate, persisted] = await Promise.all([
			storage?.estimate?.().catch(() => undefined),
			storage?.persisted?.().catch(() => undefined)
		]);
		return {
			usageBytes: estimate?.usage ?? null,
			quotaBytes: estimate?.quota ?? null,
			persisted: persisted ?? null
		};
	}

	function readCache(client: QueryClient): CacheEntry[] {
		const newestById: Record<string, number> = {};
		for (const query of client.getQueryCache().getAll()) {
			const [{ _id }] = query.queryKey as [{ _id: string }];
			if (!(_id in CACHE_LABELS) || query.state.data === undefined) continue;
			const updatedAt = query.state.dataUpdatedAt;
			newestById[_id] = Math.max(newestById[_id] ?? 0, updatedAt);
		}
		const entries: CacheEntry[] = [];
		for (const [id, label] of Object.entries(CACHE_LABELS)) {
			const updatedAt = newestById[id];
			if (updatedAt !== undefined) entries.push({ label: label(), updatedAt });
		}
		return entries;
	}

	async function copyReport() {
		if (!snapshot) return;
		try {
			await navigator.clipboard.writeText(formatReport(snapshot, capturedAt));
			toastService.add(m.diagnostics_report_copied(), 'success');
		} catch (error) {
			console.error('Failed to copy diagnostics report:', error);
			toastService.add(m.diagnostics_copy_failed(), 'error');
		}
	}

	// The reload after this fetches everything afresh, which is why it is offered
	// online only: offline it would leave nothing to open the app with. The session
	// cookie is not touched, so the user stays signed in.
	async function resetAndReload() {
		// The connection can drop while the confirmation is open.
		if (!reachability.current) {
			toastService.add(m.diagnostics_reset_offline(), 'error');
			return;
		}
		isResetting = true;
		try {
			queryClient.clear();
			await del(QUERY_CACHE_KEY);
			if ('caches' in window) {
				const keys = await caches.keys();
				await Promise.all(keys.map((key) => caches.delete(key)));
			}
			if ('serviceWorker' in navigator) {
				const registrations = await navigator.serviceWorker.getRegistrations();
				await Promise.all(registrations.map((registration) => registration.unregister()));
			}
		} catch (error) {
			// Whatever was cleared stays cleared; the reload still gets a fresh bundle.
			console.error('Diagnostics reset failed part-way:', error);
		}
		location.reload();
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Content class="sm:max-w-md">
		<Dialog.Header>
			<Dialog.Title class="flex items-center gap-2">
				<Stethoscope class="size-5 text-muted-foreground" />
				{m.diagnostics_title()}
			</Dialog.Title>
			<Dialog.Description>
				{m.diagnostics_description()}
			</Dialog.Description>
		</Dialog.Header>

		<div class="flex flex-col gap-4">
			{#each sections as section (section.title)}
				<section>
					<h3 class="mb-1 text-sm font-semibold text-foreground">
						{section.title}
					</h3>
					<dl class="divide-y divide-border rounded-xl border border-border text-sm">
						{#each section.rows as row (row.label)}
							<div class="flex items-baseline justify-between gap-3 px-3 py-2">
								<dt class="text-muted-foreground">{row.label}</dt>
								<dd class="min-w-0 text-right font-medium wrap-break-word">{row.value}</dd>
							</div>
						{/each}
					</dl>
				</section>
			{/each}
		</div>

		<Dialog.Footer class="flex flex-col gap-2 sm:flex-col">
			<Button class="w-full" disabled={!snapshot} onclick={copyReport}>
				<Copy data-icon="inline-start" />
				{m.diagnostics_copy_report()}
			</Button>
			<Button
				variant="outline"
				class="w-full"
				disabled={!reachability.current || isResetting}
				onclick={() => (confirmResetOpen = true)}
			>
				<RotateCcw data-icon="inline-start" />
				{m.diagnostics_reset_action()}
			</Button>
			{#if !reachability.current}
				<p class="text-center text-sm leading-relaxed text-muted-foreground">
					{m.diagnostics_reset_hint()}
				</p>
			{/if}
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>

<AlertDialog.Root bind:open={confirmResetOpen}>
	<AlertDialog.Content>
		<AlertDialog.Header>
			<AlertDialog.Title>{m.diagnostics_reset_confirm_title()}</AlertDialog.Title>
			<AlertDialog.Description>
				{m.diagnostics_reset_confirm_description()}
			</AlertDialog.Description>
		</AlertDialog.Header>
		<AlertDialog.Footer>
			<AlertDialog.Cancel>{m.common_cancel()}</AlertDialog.Cancel>
			<AlertDialog.Action disabled={!reachability.current} onclick={resetAndReload}>
				{m.common_reset()}
			</AlertDialog.Action>
		</AlertDialog.Footer>
	</AlertDialog.Content>
</AlertDialog.Root>
