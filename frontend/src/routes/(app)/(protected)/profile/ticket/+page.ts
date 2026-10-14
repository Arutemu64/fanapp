import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

export const load: PageLoad = () => ({ title: m.profile_menu_ticket() });
