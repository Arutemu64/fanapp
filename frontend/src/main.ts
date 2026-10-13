import { VueQueryPlugin } from '@tanstack/vue-query';
import { createPinia } from 'pinia';
import { createApp } from 'vue';

import './app.css';

import App from './App.vue';
import { createRestoredQueryClient } from './bootstrap.js';
import { installChunkRecovery } from './chunkRecovery.js';
import { createAppRouter } from './router/index.js';
import { initSentry } from './sentry.js';

const queryClient = await createRestoredQueryClient();
const router = createAppRouter(queryClient);

const app = createApp(App);
app.use(createPinia());
app.use(VueQueryPlugin, { queryClient });
app.use(router);

initSentry(app, router);
installChunkRecovery(router);

// First paint is the resolved page, not an empty shell: the boot splash in
// index.html stays until the initial route's loaders have run.
await router.isReady();
app.mount('#app');
