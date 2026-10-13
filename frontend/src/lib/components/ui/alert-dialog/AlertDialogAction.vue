<script setup lang="ts">
import type { AlertDialogActionProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import type { ButtonVariants } from '#lib/components/ui/button/index.js'
import { reactiveOmit } from '@vueuse/core'
import { AlertDialogAction } from 'reka-ui'
import { cn } from '#lib/utils.js'
import { buttonVariants } from '#lib/components/ui/button/index.js'

const props = withDefaults(
  defineProps<AlertDialogActionProps & {
    class?: HTMLAttributes['class']
    variant?: ButtonVariants['variant']
    size?: ButtonVariants['size']
  }>(),
  {
    variant: 'default',
    size: 'default',
  },
)

const delegatedProps = reactiveOmit(props, 'class', 'variant', 'size')
</script>

<template>
  <AlertDialogAction
    data-slot="alert-dialog-action"
    v-bind="delegatedProps"
    :class="cn('', buttonVariants({ variant, size }), props.class)"
  >
    <slot />
  </AlertDialogAction>
</template>
