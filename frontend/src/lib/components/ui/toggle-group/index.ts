// Each part is exported twice: under its full name and as a short name (`Root`, `Content`, …) so
// `import * as X from '…/index.js'` call sites read `X.Root`, `X.Content`.
export { default as ToggleGroup } from './ToggleGroup.vue';
export { default as Root } from './ToggleGroup.vue';
export { default as ToggleGroupItem } from './ToggleGroupItem.vue';
export { default as Item } from './ToggleGroupItem.vue';
