import type { RequestHandler } from './$types';

// Liveness probe for Docker/orchestration. Deliberately dependency-free: it does
// not touch the backend, cookies, or the user session, so it stays green as long
// as the SvelteKit server itself is serving requests.
export const GET: RequestHandler = () => {
	return new Response('OK', {
		status: 200,
		headers: { 'content-type': 'text/plain' }
	});
};
