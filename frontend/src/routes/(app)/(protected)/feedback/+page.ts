import { m } from '#lib/paraglide/messages.js';

import type { PageLoad } from './$types';

// Opened offline, the form still works: a message waits in the write queue
// (ADR-0038) and goes out when the connection returns.
export const load: PageLoad = () => ({ title: m.feedback_title() });
