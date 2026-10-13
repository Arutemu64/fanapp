<script setup lang="ts">
import type { PWAInstallElement } from '@khmyznikov/pwa-install';

import * as Sentry from '@sentry/vue';
import { useEventListener } from '@vueuse/core';
import {
	onBeforeUnmount,
	onErrorCaptured,
	onMounted,
	provide,
	ref,
	useTemplateRef,
	watch,
	watchEffect
} from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuery, useQueryClient } from '@tanstack/vue-query';

import {
	countUnreadNotificationsQueryKey,
	getPublicConfigQueryKey,
	getScheduleQueryKey,
	getSyncSourcesQueryKey,
	getVotingStatusQueryKey,
	listScheduleChangesQueryKey,
	listUserNotificationsQueryKey
} from '#lib/api/generated/@tanstack/vue-query.gen.js';
import { currentUserOptions, watchApiResponses } from '#lib/api/index.js';
import ErrorState from '#lib/components/ErrorState.vue';
import Toaster from '#lib/components/ui/sonner/Sonner.vue';
import UpdatePrompt from '#lib/components/UpdatePrompt.vue';
import { createEventsClient, eventsClientKey } from '#lib/services/events.js';
import { startReachabilityMonitor } from '#lib/services/reachabilityMonitor.js';
import { usePwaStore } from '#lib/stores/pwa.js';
import { useThemeStore } from '#lib/stores/theme.js';
import { registerServiceWorker } from '#lib/utils/serviceWorker.js';
import { reportUnexpectedError } from '#lib/utils/reportError.js';
import type { ShownError } from '#lib/router/load.js';

const queryClient = useQueryClient();
const router = useRouter();
const route = useRoute();

const eventsClient = createEventsClient(queryClient);
provide(eventsClientKey, eventsClient);
const pwa = usePwaStore();
// Applies the saved theme before the first screen renders.
useThemeStore();

// iOS Safari applies :active only while a touch listener sits on the element or an
// ancestor, so without this the press half of the `hover` variant (app.css) never
// shows on an iPhone. Empty and passive: it never delays scrolling.
// https://web.dev/articles/add-touch-to-your-site
useEventListener(document, 'touchstart', () => {}, { passive: true });

const pwaInstall = useTemplateRef<PWAInstallElement>('pwaInstall');

onMounted(() => {
	// Remove the static boot splash (in index.html) now that the app has mounted.
	document.getElementById('app-splash')?.remove();

	// Registered by hand so a rejected register() gets a .catch() — see
	// registerServiceWorker.
	registerServiceWorker();

	// Exempt the saved offline screens from eviction under storage pressure, so a
	// full phone can't drop the programme before the festival. Only when
	// installed: Chrome and Safari grant or deny silently, an installed app
	// among WebKit's grounds for granting
	// (https://webkit.org/blog/14403/updates-to-storage-policy/), but Firefox
	// asks with a popup, which a passing visitor shouldn't get
	// (https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria).
	if (pwa.isInstalled) {
		void navigator.storage?.persist().catch(() => {
			// Denied or unsupported: the cache stays best-effort.
		});
	}

	if (pwaInstall.value) stopPwaAttach = pwa.attach(pwaInstall.value);
});

let stopPwaAttach: (() => void) | undefined;

// Each teardown drops listeners, interceptors or a recovery poll, so dev HMR
// re-creating this component doesn't stack duplicates.
const stopMonitor = startReachabilityMonitor();
const stopWatching = watchApiResponses(queryClient, router);

// SSE carries change signals only, so each event marks the queries it affects
// stale: those on screen refetch at once, the rest when next shown. Keys match
// by prefix, so a list key also covers its infinite (paginated) variant.

// The change log has no event of its own: every change that adds a row to it
// (create, undo) also broadcasts schedule_updated, a superset of the moments it
// goes stale. The extra refetch that costs — a bulk import touches the schedule
// but records no change row — is one request for the few staff watching it.
function handleScheduleUpdated() {
	void queryClient.invalidateQueries({ queryKey: getScheduleQueryKey() });
	void queryClient.invalidateQueries({ queryKey: listScheduleChangesQueryKey() });
}

// The voting window is part of the festival config, so the voting status moves
// with it.
function handleConfigUpdated() {
	void queryClient.invalidateQueries({ queryKey: getPublicConfigQueryKey() });
	void queryClient.invalidateQueries({ queryKey: getVotingStatusQueryKey() });
}

function handleNotificationCreated() {
	void queryClient.invalidateQueries({ queryKey: countUnreadNotificationsQueryKey() });
	void queryClient.invalidateQueries({ queryKey: listUserNotificationsQueryKey() });
}

// The payload only names the run; GET /sync/sources stays the source of truth.
function handleSyncRunUpdated() {
	void queryClient.invalidateQueries({ queryKey: getSyncSourcesQueryKey() });
}

eventsClient.on('schedule_updated', handleScheduleUpdated);
eventsClient.on('config_updated', handleConfigUpdated);
eventsClient.on('notification_created', handleNotificationCreated);
eventsClient.on('sync_run_updated', handleSyncRunUpdated);

const { data: user } = useQuery(() => currentUserOptions());

watchEffect(() => {
	if (user.value) {
		Sentry.setUser({
			id: String(user.value.id),
			username: user.value.username ?? undefined
		});
	} else {
		Sentry.setUser(null);
	}
});

// A component that throws while rendering takes over the screen with the error
// state instead of leaving a blank page. It clears on the next navigation, so
// the user can leave through a link or the browser's Back.
const renderError = ref<ShownError>();

onErrorCaptured((error) => {
	renderError.value = {
		status: 500,
		message: 'В приложении что-то сломалось. Попробуй обновить страницу.',
		code: 'UNKNOWN',
		errorId: reportUnexpectedError(error)
	};
	return false;
});

watch(
	() => route.fullPath,
	() => {
		renderError.value = undefined;
	}
);

onBeforeUnmount(() => {
	stopMonitor();
	stopWatching();
	stopPwaAttach?.();
	eventsClient.off('schedule_updated', handleScheduleUpdated);
	eventsClient.off('config_updated', handleConfigUpdated);
	eventsClient.off('notification_created', handleNotificationCreated);
	eventsClient.off('sync_run_updated', handleSyncRunUpdated);
	// destroy() (not disconnect()) also unhooks the client's global
	// window/document listeners, so no zombie stream can resurrect —
	// matters mostly for dev HMR, which re-creates the root component.
	eventsClient.destroy();
});
</script>

<template>
	<ErrorState v-if="renderError" variant="fullscreen" :error="renderError" />
	<RouterView v-else />

	<Toaster />

	<!--
		Single instance of the install dialog. `manual-chrome`/`manual-apple` keep it
		hidden until we open it from our own buttons via the PWA store's
		showInstallDialog(). Locale (incl. Russian) is auto-detected by the library
		from the browser.
	-->
	<pwa-install
		ref="pwaInstall"
		manual-chrome
		manual-apple
		manifest-url="/manifest.json"
		name="ФАН ФАН"
		icon="/icons/icon-512.png"
	></pwa-install>

	<!-- Prompts the user to reload when a new build has been cached by the SW. -->
	<UpdatePrompt />
</template>
