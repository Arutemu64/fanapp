// Each part is exported twice: under its full name and as a short name (`Root`, `Content`, …) so
// `import * as X from '…/index.js'` call sites read `X.Root`, `X.Content`.
export { default as Dialog } from './Dialog.vue';
export { default as Root } from './Dialog.vue';
export { default as DialogClose } from './DialogClose.vue';
export { default as Close } from './DialogClose.vue';
export { default as DialogContent } from './DialogContent.vue';
export { default as Content } from './DialogContent.vue';
export { default as DialogDescription } from './DialogDescription.vue';
export { default as Description } from './DialogDescription.vue';
export { default as DialogFooter } from './DialogFooter.vue';
export { default as Footer } from './DialogFooter.vue';
export { default as DialogHeader } from './DialogHeader.vue';
export { default as Header } from './DialogHeader.vue';
export { default as DialogOverlay } from './DialogOverlay.vue';
export { default as Overlay } from './DialogOverlay.vue';
export { default as DialogTitle } from './DialogTitle.vue';
export { default as Title } from './DialogTitle.vue';
export { default as DialogTrigger } from './DialogTrigger.vue';
export { default as Trigger } from './DialogTrigger.vue';
