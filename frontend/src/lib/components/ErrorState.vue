<script setup lang="ts">
import { AlertCircle, ArrowLeft, Home, Lock, RotateCw } from '@lucide/vue';
import { computed } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import type { ShownError } from '#lib/router/load.js';

import { Button } from '#lib/components/ui/button/index.js';
import * as Card from '#lib/components/ui/card/index.js';
import { probeReachability, reachability } from '#lib/services/reachability.js';
import { statusTitle } from '#lib/utils/errorTitle.js';

type Variant = 'fullscreen' | 'inline';

// `fullscreen` takes over the whole viewport (root errors: 404, auth, root load
// failures). `inline` fills the content area only, so the app shell — navbar,
// sidebar, bottom nav — stays visible and navigable around it.
// `error` is the error to show. Without it the current route's `meta.error` (set by
// the router when a loader failed) is shown. Prefer passing it: a failing boundary
// elsewhere (the navbar's bell) must not replace this page's message and «Код ошибки».
// A page showing a failed query passes one too, status included: the page itself
// rendered fine. It also passes `onRetry` (`@retry`), which refetches that query
// instead of reloading the whole app. Declared as a prop, not an emit, because its
// presence picks the behaviour.
const {
	variant = 'fullscreen',
	error,
	onRetry
} = defineProps<{
	variant?: Variant;
	error?: ShownError;
	onRetry?: () => void;
}>();

const route = useRoute();

const shownError = computed(() => error ?? route.meta.error);
const status = computed(() => shownError.value?.status ?? 500);
const errorMessage = computed(() => shownError.value?.message);
const errorId = computed(() => shownError.value?.errorId);

// Most load failures while offline surface here as a 500/503. Detect the real
// cause (backend unreachable) and show a calm connectivity page instead of a
// scary server-error screen.
const online = computed(() => reachability.current);
// A genuine 403/404 is a real server answer — never reframe it as offline.
const offline = computed(() => !online.value && status.value !== 403 && status.value !== 404);

// Within an offline state, tell the two causes apart so we never blame the
// user's internet for a server outage. `navigator.onLine === false` is a
// trustworthy negative — the device really has no connection; otherwise the
// device is online but the server can't be reached (API down, captive portal,
// dead VPN), for which "нет связи с сервером" is the honest, non-blaming framing.
const deviceOffline = computed(() => !reachability.deviceOnline);

const title = computed(() => {
	if (!offline.value) return statusTitle(status.value);
	return deviceOffline.value ? 'Нет интернета' : 'Нет связи с сервером';
});

// A genuine 403 gets the lock icon; everything else (including offline, which
// is never a 403) gets the generic alert icon. Offline is the only yellow
// state; all others are red.
const statusIcon = computed(() => (status.value === 403 ? Lock : AlertCircle));
const iconColorClass = computed(() =>
	offline.value ? 'bg-warning/15 text-warning' : 'bg-destructive/15 text-destructive'
);

const description = computed(() => {
	if (offline.value && deviceOffline.value)
		return 'Проверь подключение к сети. Часть данных доступна офлайн.';
	if (offline.value) return 'Не удаётся связаться с сервером. Часть данных доступна офлайн.';
	if (errorMessage.value) return errorMessage.value;
	if (status.value === 403) return 'У тебя нет прав для просмотра этой страницы.';
	if (status.value === 404)
		return 'Похоже, эта страница не существует, была удалена или перенесена.';
	return 'Произошла непредвиденная ошибка на сервере или отсутствует интернет-соединение.';
});

const canRetry = computed(() => offline.value || status.value >= 500);

// Fullscreen owns the viewport background; inline inherits the shell's surface.
const wrapperClass = computed(() =>
	variant === 'fullscreen'
		? 'flex min-h-dvh items-center justify-center bg-background px-4 py-6 sm:py-10'
		: 'flex min-h-[60dvh] items-center justify-center px-4 py-6'
);

function handleGoBack() {
	window.history.back();
}

function handleRetry() {
	if (onRetry) {
		// While the app counts the server as unreachable, TanStack pauses the
		// refetch, and the background recovery poll can be up to 30s away. Checking
		// now lets a tap resume every paused query the moment the server answers.
		if (!online.value) void probeReachability();
		onRetry();
		return;
	}
	window.location.reload();
}
</script>

<template>
	<div :class="wrapperClass">
		<Card.Root class="w-full max-w-md rounded-2xl p-6 text-center sm:p-8">
			<div class="flex flex-col items-center justify-center">
				<div
					class="mb-4 flex h-16 w-16 items-center justify-center rounded-full"
					:class="iconColorClass"
				>
					<component :is="statusIcon" class="h-8 w-8" />
				</div>

				<span class="mb-1 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
					{{ offline ? 'Офлайн' : `Ошибка ${status}` }}
				</span>

				<h2 class="mb-2 text-xl font-bold text-foreground sm:text-2xl">
					{{ title }}
				</h2>

				<p class="mb-6 text-sm text-muted-foreground">
					{{ description }}
				</p>

				<!-- Something a user can quote in feedback; matches the error_id tag on the
				     GlitchTip event (see reportUnexpectedError). -->
				<p v-if="errorId" class="-mt-4 mb-6 text-xs text-muted-foreground">
					Код ошибки: <span class="font-mono select-all">{{ errorId }}</span>
				</p>

				<div class="flex w-full flex-col gap-2">
					<Button v-if="canRetry" class="w-full" @click="handleRetry">
						<RotateCw data-icon="inline-start" />
						Попробовать снова
					</Button>

					<Button as-child :variant="canRetry ? 'outline' : 'default'" class="w-full">
						<RouterLink to="/">
							<Home data-icon="inline-start" />
							На главную
						</RouterLink>
					</Button>

					<Button type="button" variant="ghost" class="w-full" @click="handleGoBack">
						<ArrowLeft data-icon="inline-start" />
						Вернуться назад
					</Button>
				</div>
			</div>
		</Card.Root>
	</div>
</template>
