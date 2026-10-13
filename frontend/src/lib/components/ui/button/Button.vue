<script setup lang="ts">
import type { PrimitiveProps } from 'reka-ui'
import type { ButtonHTMLAttributes, HTMLAttributes } from 'vue'
import type { ButtonVariants } from '.'
import { Primitive } from 'reka-ui'
import { computed } from 'vue'
import { cn } from '#lib/utils.js'
import { buttonVariants } from '.'

interface Props extends PrimitiveProps {
  variant?: ButtonVariants['variant']
  size?: ButtonVariants['size']
  class?: HTMLAttributes['class']
  type?: ButtonHTMLAttributes['type']
  /** External link target; renders an `<a>`. Internal links use `as-child` + `RouterLink`. */
  href?: string
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  as: 'button',
  type: 'button',
})

const tag = computed(() => (props.href === undefined ? props.as : 'a'))

// A native button needs `type` (default "button", so a Button inside a <form> never
// submits by accident) and `disabled`. Any other element (`<a>`, a RouterLink via
// `as-child`) cannot be disabled natively and is announced as a disabled link instead.
const isNativeButton = computed(() => !props.asChild && tag.value === 'button')
const isDisabledLink = computed(() => !isNativeButton.value && props.disabled === true)
</script>

<template>
  <Primitive
    data-slot="button"
    :data-variant="variant"
    :data-size="size"
    :as="tag"
    :as-child="asChild"
    :type="isNativeButton ? type : undefined"
    :disabled="isNativeButton ? disabled : undefined"
    :href="isDisabledLink ? undefined : href"
    :aria-disabled="isDisabledLink ? 'true' : undefined"
    :role="isDisabledLink ? 'link' : undefined"
    :tabindex="isDisabledLink ? -1 : undefined"
    :class="cn(buttonVariants({ variant, size }), props.class)"
  >
    <slot />
  </Primitive>
</template>
