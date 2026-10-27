import { paraglideVitePlugin } from '@inlang/paraglide-js';
import { sentrySvelteKit } from '@sentry/sveltekit';
import adapter from '@sveltejs/adapter-static';
import { enhancedImages } from '@sveltejs/enhanced-img';
import { sveltekit } from '@sveltejs/kit/vite';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import tailwindcss from '@tailwindcss/vite';
import { mdsvex } from 'mdsvex';
import { fileURLToPath } from 'node:url';
import Icons from 'unplugin-icons/vite';
import { loadEnv } from 'vite';
import { defineConfig } from 'vitest/config';

const rootDir = fileURLToPath(new URL('..', import.meta.url));

export default defineConfig(({ mode }) => {
	const env = loadEnv(mode, rootDir, '');

	const sentryUpload = {
		org: env.SENTRY_ORG,
		project: env.SENTRY_PROJECT,
		sentryUrl: env.SENTRY_URL,
		authToken: env.SENTRY_AUTH_TOKEN
	};
	const canUploadSourceMaps = Object.values(sentryUpload).every(Boolean);

	return {
		envDir: rootDir,
		define: {
			__APP_VERSION__: JSON.stringify(env.APP_VERSION ?? ''),
			__APP_BUILD__: JSON.stringify(env.APP_BUILD ?? '')
		},
		plugins: [
			sentrySvelteKit({
				...sentryUpload,
				autoUploadSourceMaps: canUploadSourceMaps,
				release: {
					name: env.APP_BUILD || undefined
				}
			}),
			tailwindcss(),
			paraglideVitePlugin({
				project: './project.inlang',
				outdir: './src/lib/paraglide',
				strategy: ['baseLocale'],
				emitTsDeclarations: true
			}),
			enhancedImages(),
			sveltekit({
				extensions: ['.svelte', '.md'],
				preprocess: [mdsvex({ extensions: ['.md'] }), vitePreprocess()],
				env: { dir: '..' },
				adapter: adapter({ fallback: '200.html' }),
				serviceWorker: { register: false }
			}),
			Icons({
				compiler: 'svelte'
			})
		],
		optimizeDeps: {
			include: [
				'workbox-core',
				'workbox-expiration',
				'workbox-precaching',
				'workbox-routing',
				'workbox-strategies'
			]
		},
		test: {
			include: ['src/**/*.test.ts'],
			environment: 'node',
			restoreMocks: true,
			unstubGlobals: true,
			unstubEnvs: true,
			fsModuleCache: true
		},
		resolve: process.env.VITEST ? { conditions: ['browser'] } : undefined,
		server: {
			host: true,
			allowedHosts: true,
			port: Number(env.FRONTEND_PORT ?? 3000),
			strictPort: true,
			proxy: {
				'/api': {
					target: env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',
					changeOrigin: true,
					rewrite: (path) => path.replace(/^\/api/, '')
				}
			}
		}
	};
});
