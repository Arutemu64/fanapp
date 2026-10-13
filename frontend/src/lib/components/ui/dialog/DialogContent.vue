<script setup lang="ts">
import type { DialogContentEmits, DialogContentProps } from 'reka-ui';
import type { HTMLAttributes } from 'vue';

import { XIcon } from '@lucide/vue';
import { reactiveOmit } from '@vueuse/core';
import { DialogClose, DialogContent, DialogPortal, useForwardPropsEmits } from 'reka-ui';
import { computed, onWatcherCleanup, ref, useTemplateRef, watchEffect } from 'vue';

import { Button } from '#lib/components/ui/button/index.js';
import { cn } from '#lib/utils.js';
import { keyboardInset } from '#lib/utils/keyboardInset.js';

import DialogOverlay from './DialogOverlay.vue';

const props = withDefaults(
	defineProps<
		DialogContentProps & { class?: HTMLAttributes['class']; showCloseButton?: boolean }
	>(),
	{
		showCloseButton: true
	}
);

const emits = defineEmits<DialogContentEmits>();

defineOptions({
	inheritAttrs: false
});

const delegatedProps = reactiveOmit(props, 'class', 'showCloseButton');

const forwarded = useForwardPropsEmits(delegatedProps, emits);

// On a phone the sheet is fixed to the layout viewport's bottom edge, which an
// on-screen keyboard covers without moving it (see keyboardInset). While the
// sheet is open, track the covered strip and lift the sheet's content above
// it with padding — the sheet itself stays anchored, as a native one does.
const content = useTemplateRef('content');
const coveredByKeyboard = ref(0);
const visibleHeight = ref(0);

// The wrapper is instantiated while the dialog is closed; the reka content (and so the
// template ref) exists only while it is open, which is when the listeners belong.
watchEffect(() => {
	const viewport = window.visualViewport;
	if (!content.value || !viewport) return;

	const update = () => {
		coveredByKeyboard.value = keyboardInset(window.innerHeight, viewport);
		visibleHeight.value = viewport.height;
	};
	update();
	// iOS fires `scroll`, not `resize`, when it pans to a focused field.
	viewport.addEventListener('resize', update);
	viewport.addEventListener('scroll', update);
	onWatcherCleanup(() => {
		viewport.removeEventListener('resize', update);
		viewport.removeEventListener('scroll', update);
		coveredByKeyboard.value = 0;
	});
});

const keyboardStyle = computed(() =>
	coveredByKeyboard.value > 0
		? {
				'--keyboard-inset': `${coveredByKeyboard.value}px`,
				'--visible-height': `${visibleHeight.value}px`
			}
		: undefined
);
</script>

<template>
	<DialogPortal>
		<DialogOverlay />
		<DialogContent
			ref="content"
			data-slot="dialog-content"
			v-bind="{ ...$attrs, ...forwarded }"
			:style="keyboardStyle"
			:class="
				cn(
					'fixed z-50 grid w-full gap-6 bg-popover p-6 text-sm text-popover-foreground ring-1 ring-foreground/10 outline-none data-open:animate-in data-closed:animate-out',
					// Phones: a bottom sheet — thumb-reachable, clear of the home indicator, and
					// scrolling its body (below) when taller than the screen. The easing is iOS's
					// sheet curve (the one Vaul uses).
					'max-sm:inset-x-0 max-sm:bottom-0 max-sm:flex max-sm:max-h-[calc(100dvh-env(safe-area-inset-top)-2rem)] max-sm:flex-col max-sm:rounded-t-2xl max-sm:pb-[calc(1.5rem+env(safe-area-inset-bottom))] max-sm:duration-250 max-sm:ease-[cubic-bezier(0.32,0.72,0,1)] max-sm:data-open:slide-in-from-bottom max-sm:data-closed:slide-out-to-bottom',
					// Keyboard open on a phone: pad the content clear of it (the inset replaces
					// the home-indicator inset, which the keyboard covers anyway), and cap the
					// height so the sheet's top stays inside what is still visible.
					coveredByKeyboard > 0 &&
						'max-sm:max-h-[calc(var(--visible-height)+var(--keyboard-inset)-1rem)] max-sm:pb-[calc(1.5rem+var(--keyboard-inset))]',
					// sm and up: a centred dialog.
					'sm:top-1/2 sm:left-1/2 sm:max-w-md sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-2xl sm:duration-100 sm:data-open:fade-in-0 sm:data-open:zoom-in-95 sm:data-closed:fade-out-0 sm:data-closed:zoom-out-95',
					props.class
				)
			"
		>
			<!-- On phones the body scrolls, not the sheet, so the absolutely positioned close
        button stays in view on a tall form. `contents` elsewhere keeps the children as
        direct grid items. The 1-unit inset stops the scroller clipping focus rings. -->
			<div
				class="contents max-sm:-m-1 max-sm:grid max-sm:min-h-0 max-sm:gap-6 max-sm:overflow-y-auto max-sm:overscroll-contain max-sm:p-1"
			>
				<slot />
			</div>

			<DialogClose v-if="showCloseButton" data-slot="dialog-close" as-child>
				<Button variant="ghost" class="absolute top-4 right-4" size="icon-sm">
					<XIcon />
					<span class="sr-only">Закрыть</span>
				</Button>
			</DialogClose>
		</DialogContent>
	</DialogPortal>
</template>
