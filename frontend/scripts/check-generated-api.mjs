import { createClient } from '@hey-api/openapi-ts';
import { mkdir, mkdtemp, readdir, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Mirrors the drift check the old openapi-typescript generator had (`pnpm
// generate-api:check`, docs/api.md "Both generated artifacts are enforced in
// CI"): regenerate the hey-api client into a throwaway directory and diff it
// against the committed `src/lib/api/client/`, since `@hey-api/openapi-ts` has
// no built-in `--check` flag — its `createClient()` only ever writes to disk.

const frontendRoot = fileURLToPath(new URL('..', import.meta.url));
const committedDir = path.join(frontendRoot, 'src/lib/api/client');

// The throwaway output must live INSIDE the frontend project, not the OS temp
// dir: postProcess's prettier step resolves `.prettierrc` by walking up from
// the file being formatted, and a path under `/tmp` finds no such config —
// silently falling back to Prettier's defaults and making every regenerated
// file "differ" from the committed, project-formatted one. `.api-check-tmp/`
// is gitignored.
const tempRoot = path.join(frontendRoot, '.api-check-tmp');

async function listFilesRecursive(dir) {
	const entries = await readdir(dir, { withFileTypes: true });
	const files = await Promise.all(
		entries.map(async (entry) => {
			const fullPath = path.join(dir, entry.name);
			if (entry.isDirectory()) return listFilesRecursive(fullPath);
			return [fullPath];
		})
	);
	return files.flat();
}

await mkdir(tempRoot, { recursive: true });
const tempDir = await mkdtemp(path.join(tempRoot, 'check-'));

try {
	await createClient({
		input: path.join(frontendRoot, '../shared/openapi/openapi.json'),
		logs: { level: 'silent' },
		// Must mirror openapi-ts.config.ts exactly (including postProcess), or
		// this diffs against a differently-formatted regeneration every time.
		output: { path: tempDir, postProcess: ['prettier'] },
		plugins: [
			'@hey-api/client-fetch',
			'@hey-api/typescript',
			'@hey-api/sdk',
			'@tanstack/svelte-query'
		]
	});

	const [committedFiles, generatedFiles] = await Promise.all([
		listFilesRecursive(committedDir),
		listFilesRecursive(tempDir)
	]);

	const relative = (base) => (file) => path.relative(base, file);
	const committedRelative = new Set(committedFiles.map(relative(committedDir)));
	const generatedRelative = new Set(generatedFiles.map(relative(tempDir)));

	const missing = [...generatedRelative].filter((file) => !committedRelative.has(file));
	const extra = [...committedRelative].filter((file) => !generatedRelative.has(file));

	const mismatched = [];
	for (const file of generatedRelative) {
		if (!committedRelative.has(file)) continue;
		const [committed, generated] = await Promise.all([
			readFile(path.join(committedDir, file), 'utf8'),
			readFile(path.join(tempDir, file), 'utf8')
		]);
		if (committed !== generated) mismatched.push(file);
	}

	if (missing.length || extra.length || mismatched.length) {
		console.error('src/lib/api/client/ is out of date with shared/openapi/openapi.json.');
		if (missing.length) console.error('  Missing files:', missing.join(', '));
		if (extra.length) console.error('  Stale files:', extra.join(', '));
		if (mismatched.length) console.error('  Changed files:', mismatched.join(', '));
		console.error('Regenerate it with: just frontend-generate-api');
		process.exitCode = 1;
	} else {
		console.log('Up to date: src/lib/api/client/');
	}
} finally {
	await rm(tempDir, { recursive: true, force: true });
}
