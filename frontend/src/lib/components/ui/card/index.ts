// Each part is exported twice: under its full name and as a short name (`Root`, `Content`, …) so
// `import * as X from '…/index.js'` call sites read `X.Root`, `X.Content`.
export { default as Card } from './Card.vue';
export { default as Root } from './Card.vue';
export { default as CardAction } from './CardAction.vue';
export { default as Action } from './CardAction.vue';
export { default as CardContent } from './CardContent.vue';
export { default as Content } from './CardContent.vue';
export { default as CardDescription } from './CardDescription.vue';
export { default as Description } from './CardDescription.vue';
export { default as CardFooter } from './CardFooter.vue';
export { default as Footer } from './CardFooter.vue';
export { default as CardHeader } from './CardHeader.vue';
export { default as Header } from './CardHeader.vue';
export { default as CardTitle } from './CardTitle.vue';
export { default as Title } from './CardTitle.vue';
