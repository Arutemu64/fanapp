import { readFileSync } from 'node:fs';
import { defineConfig } from 'vite';

export default defineConfig({
	appType: 'custom',
	build: { outDir: 'build' },
	plugins: [
		{
			name: 'app-shell-fallback',
			configurePreviewServer(server) {
				const shell = readFileSync(new URL('../build/200.html', import.meta.url));
				return () => {
					server.middlewares.use((request, response, next) => {
						const assetOrApi = /^\/(?:_app|api)(?:\/|\?|$)/.test(request.url ?? '');
						if (assetOrApi || !request.headers.accept?.includes('text/html')) {
							next();
							return;
						}
						response.setHeader('Content-Type', 'text/html; charset=utf-8');
						response.setHeader('Cache-Control', 'no-cache');
						response.end(shell);
					});
				};
			}
		}
	]
});
