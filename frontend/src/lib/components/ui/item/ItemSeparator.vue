<script setup lang="ts">
import type { SeparatorProps } from 'reka-ui'
import type { HTMLAttributes } from 'vue'
import { cn } from '#lib/utils.js'
import { Separator } from '#lib/components/ui/separator/index.js'

const props = defineProps<
  SeparatorProps & { class?: HTMLAttributes['class'] }
>()
</script>

<template>
  <Separator
    data-slot="item-separator"
    orientation="horizontal"
    :class="cn('my-2', props.class)"
  />
</template>
