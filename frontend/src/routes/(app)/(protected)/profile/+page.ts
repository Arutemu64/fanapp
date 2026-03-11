import type { PageLoad } from './$types';
import { client } from '$lib/api';

export const load: PageLoad = async ({ fetch, depends }) => {
	depends('app:push-subscriptions');
	depends('app:social-accounts');

	const [{ data: pushSubscriptions }, { data: socialAccounts }] = await Promise.all([
		client.GET('/push', { fetch }),
		client.GET('/me/social-accounts', { fetch })
	]);

	return {
		pushSubscriptions: pushSubscriptions ?? [],
		socialAccounts: socialAccounts ?? []
	};
};
