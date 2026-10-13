<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '#lib/utils.js'

const props = withDefaults(defineProps<{
  class?: HTMLAttributes['class']
  size?: 'default' | 'sm'
  /**
   * Opt a card into a semantic container (e.g. `article` for a self-contained
   * content tile). Stays per-instance and defaults to `div` because most cards
   * — form panels, the login/error card — are not articles. Local addition
   * upstream lacks (shadcn ships Card as a bare div, issue #10301 open); a
   * shadcn-vue update will drop this prop — keep it on merge.
   */
  as?: 'div' | 'article' | 'section'
}>(), {
  size: 'default',
  as: 'div',
})
</script>

<template>
  <component
    :is="as"
    data-slot="card"
    :data-size="size"
    :class="cn('ring-foreground/10 bg-card text-card-foreground gap-6 overflow-hidden rounded-xl py-6 text-sm shadow-xs ring-1 has-[>img:first-child]:pt-0 data-[size=sm]:gap-4 data-[size=sm]:py-4 *:[img:first-child]:rounded-t-xl *:[img:last-child]:rounded-b-xl group/card flex flex-col', props.class)"
  >
    <slot />
  </component>
</template>
