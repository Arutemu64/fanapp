<script setup lang="ts">
import type { InputGroupButtonProps } from '.'
import { cn } from '#lib/utils.js'
import { Button } from '#lib/components/ui/button/index.js'
import { inputGroupButtonVariants } from '.'

const props = withDefaults(defineProps<InputGroupButtonProps>(), {
  size: 'xs',
  variant: 'ghost',
})
</script>

<template>
  <Button
    type="button"
    :data-size="props.size"
    :variant="props.variant"
    :class="cn(inputGroupButtonVariants({ size: props.size }), props.class)"
  >
    <slot />
  </Button>
</template>
