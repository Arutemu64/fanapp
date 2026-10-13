<script setup lang="ts">
import type { Component } from 'vue';

import * as Empty from '#lib/components/ui/empty/index.js';

defineProps<{
	// Optional leading icon (e.g. for richer empty states like voting lists).
	icon?: Component;
	// When set, renders a bold heading above the message (two-line variant).
	title?: string;
	message: string;
}>();
</script>

<!-- App-wide empty state: shadcn Empty on the app's card surface (solid border +
	bg-card + calm p-6), understated per DESIGN.md — a teaching state, not "nothing
	here". The icon stays bare and muted (default media variant) rather than a
	filled tile, keeping color for action and semantic state only.
	The default slot is an optional trailing action, e.g. a "clear search" button. -->
<template>
	<Empty.Root class="border border-solid bg-card p-6">
		<Empty.Header>
			<Empty.Media v-if="icon" class="mb-0 text-muted-foreground">
				<component :is="icon" class="size-10 sm:size-12" />
			</Empty.Media>
			<Empty.Title v-if="title" class="text-base font-bold">{{ title }}</Empty.Title>
			<Empty.Description>{{ message }}</Empty.Description>
		</Empty.Header>
		<Empty.Content v-if="$slots.default">
			<slot />
		</Empty.Content>
	</Empty.Root>
</template>
