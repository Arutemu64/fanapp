<script setup lang="ts">
import { Eye, EyeOff, Lock } from '@lucide/vue';
import { computed, ref } from 'vue';

import * as InputGroup from '#lib/components/ui/input-group/index.js';

const {
	id,
	name,
	autocomplete,
	revealLabel = 'пароль',
	placeholder = '••••••••',
	required = false,
	disabled = false,
	readonly = false,
	maxlength,
	color,
	describedby
} = defineProps<{
	id: string;
	name: string;
	autocomplete: 'current-password' | 'new-password';
	// Noun used in the toggle's aria-label, e.g. "Показать {revealLabel}".
	revealLabel?: string;
	placeholder?: string;
	required?: boolean;
	disabled?: boolean;
	readonly?: boolean;
	maxlength?: number;
	color?: 'red' | undefined;
	// Id of the error or hint that describes the field (aria-describedby).
	describedby?: string;
}>();

// `input` fires on every keystroke, like the old `oninput` callback.
defineEmits<{ input: [] }>();

const value = defineModel<string>({ default: '' });

const show = ref(false);
const invalid = computed(() => color === 'red');
const toggleLabel = computed(() =>
	show.value ? `Скрыть ${revealLabel}` : `Показать ${revealLabel}`
);

function toggleShow() {
	show.value = !show.value;
}
</script>

<template>
	<InputGroup.Root>
		<InputGroup.Addon>
			<Lock aria-hidden="true" />
		</InputGroup.Addon>
		<InputGroup.Input
			:id="id"
			v-model="value"
			:name="name"
			:type="show ? 'text' : 'password'"
			:placeholder="placeholder"
			:autocomplete="autocomplete"
			:required="required"
			:disabled="disabled"
			:readonly="readonly"
			:maxlength="maxlength"
			:aria-invalid="invalid ? true : undefined"
			:aria-describedby="describedby"
			@input="$emit('input')"
		/>
		<InputGroup.Addon align="inline-end">
			<InputGroup.Button
				size="icon-sm"
				:disabled="disabled"
				:aria-label="toggleLabel"
				:aria-pressed="show"
				@click="toggleShow"
			>
				<Eye v-if="show" />
				<EyeOff v-else />
			</InputGroup.Button>
		</InputGroup.Addon>
	</InputGroup.Root>
</template>
