// Each part is exported twice: under its full name and as a short name (`Root`, `Content`, …) so
// `import * as X from '…/index.js'` call sites read `X.Root`, `X.Content`.
export { default as Sheet } from './Sheet.vue';
export { default as Root } from './Sheet.vue';
export { default as SheetClose } from './SheetClose.vue';
export { default as Close } from './SheetClose.vue';
export { default as SheetContent } from './SheetContent.vue';
export { default as Content } from './SheetContent.vue';
export { default as SheetDescription } from './SheetDescription.vue';
export { default as Description } from './SheetDescription.vue';
export { default as SheetFooter } from './SheetFooter.vue';
export { default as Footer } from './SheetFooter.vue';
export { default as SheetHeader } from './SheetHeader.vue';
export { default as Header } from './SheetHeader.vue';
export { default as SheetTitle } from './SheetTitle.vue';
export { default as Title } from './SheetTitle.vue';
export { default as SheetTrigger } from './SheetTrigger.vue';
export { default as Trigger } from './SheetTrigger.vue';
