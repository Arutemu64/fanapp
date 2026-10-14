import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

export const load: PageLoad = () => ({ title: m.notifications_title() });
