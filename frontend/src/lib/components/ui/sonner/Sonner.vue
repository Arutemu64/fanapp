<script lang="ts" setup>
import type { ToasterProps } from 'vue-sonner';

import {
	CircleCheckIcon,
	InfoIcon,
	Loader2Icon,
	OctagonXIcon,
	TriangleAlertIcon,
	XIcon
} from '@lucide/vue';
import { reactiveOmit } from '@vueuse/core';
import { computed } from 'vue';
import { Toaster as Sonner } from 'vue-sonner';
import 'vue-sonner/style.css';

import { useThemeStore } from '#lib/stores/theme.js';
import { cn } from '#lib/utils.js';

// Two toast lanes share this one Toaster via per-toast `position` (set in
// stores/toasts.ts): action feedback at bottom-center (the default below),
// push notifications at top-right. A single object offset covers both — a
// top-anchored toast reads top/right, a bottom-anchored one reads bottom — so
// each lane clears its own chrome. The insets are CSS vars (app.css) that
// trace the top bar and the mobile-only bottom nav.
//
// swipeDirections: Sonner's default only swipes toward the toast's own edge, so a
// bottom toast could be flicked only downward, into the bottom nav. Any direction
// dismisses.
const props = withDefaults(defineProps<ToasterProps>(), {
	position: 'bottom-center',
	closeButtonPosition: 'top-right',
	containerAriaLabel: 'Всплывающие сообщения',
	offset: () => ({
		top: 'var(--toast-top-offset)',
		bottom: 'var(--toast-bottom-offset)',
		left: '1.5rem',
		right: '1.5rem'
	}),
	mobileOffset: () => ({
		top: 'var(--toast-top-offset)',
		bottom: 'var(--toast-bottom-offset)',
		left: '1rem',
		right: '1rem'
	}),
	swipeDirections: () => ['top', 'right', 'bottom', 'left']
});

const delegatedProps = reactiveOmit(props, 'class', 'toastOptions', 'theme');

const themeStore = useThemeStore();
const theme = computed(() => props.theme ?? themeStore.mode);

// Only Sonner's own options here, no overrides of its CSS (they break silently
// on upgrade). Inline styles and the variables below beat its stylesheet. The
// close button sits in the top-right corner (`closeButtonPosition`), where Carbon
// and most web toasts put it, instead of Sonner's macOS-style top-left badge.
const toastOptions = computed(() => ({
	closeButtonAriaLabel: 'Закрыть',
	actionButtonStyle: {
		background: 'var(--color-primary)',
		color: 'var(--color-primary-foreground)'
	},
	...props.toastOptions
}));
</script>

<template>
	<Sonner
		:class="cn('toaster group', props.class)"
		:theme="theme"
		:toast-options="toastOptions"
		:style="{
			'--normal-bg': 'var(--color-popover)',
			'--normal-text': 'var(--color-popover-foreground)',
			'--normal-border': 'var(--color-border)'
		}"
		v-bind="delegatedProps"
	>
		<template #success-icon>
			<CircleCheckIcon class="size-4 text-success" />
		</template>
		<template #info-icon>
			<InfoIcon class="size-4 text-info" />
		</template>
		<template #warning-icon>
			<TriangleAlertIcon class="size-4 text-warning" />
		</template>
		<template #error-icon>
			<OctagonXIcon class="size-4 text-destructive" />
		</template>
		<template #loading-icon>
			<Loader2Icon class="size-4 animate-spin" />
		</template>
		<template #close-icon>
			<XIcon class="size-4" />
		</template>
	</Sonner>
</template>
