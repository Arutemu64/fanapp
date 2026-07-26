import { defineConfig } from 'vitest/config';

// Deliberately not `vite.config.ts`: everything under test today is plain
// TypeScript, so loading the SvelteKit plugin (and the PUBLIC_* env it resolves
// at build time) would only add startup cost. Component tests would need that
// config plus a DOM environment — see docs/testing.md, "Frontend".
export default defineConfig({
	test: {
		include: ['src/**/*.test.ts'],
		environment: 'node'
	}
});
