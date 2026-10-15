import type { Snippet } from 'svelte';

/**
 * Props of a `<ParaglideMessage>` tag snippet. The component types them from the
 * message, but typescript-eslint reads `.svelte` templates without that inference
 * and treats an unannotated `{ children }` as `any`.
 */
export interface MessageTagProps {
	children?: Snippet;
}
