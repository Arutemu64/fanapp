<script setup lang="ts">
import type { SeparatorProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { reactiveOmit } from '@vueuse/core'
import { Separator } from 'reka-ui'
import { cn } from '#lib/utils.js'

const props = withDefaults(defineProps<
  SeparatorProps & { class?: HTMLAttributes['class'] }
>(), {
  orientation: 'horizontal',
  decorative: true,
})

// Vertical separators use `h-full` where upstream shadcn uses `self-stretch`: stretching
// breaks layouts here.
const delegatedProps = reactiveOmit(props, 'class')
</script>

<template>
  <Separator
    data-slot="separator"
    v-bind="delegatedProps"
    :class="
      cn(
        'shrink-0 bg-border data-[orientation=horizontal]:h-px data-[orientation=horizontal]:w-full data-[orientation=vertical]:w-px data-[orientation=vertical]:h-full',
        props.class,
      )
    "
  />
</template>
