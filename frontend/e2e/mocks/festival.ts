import type { Handlers } from './api';

import {
	GALLERY_NOW,
	notifications,
	questStanding,
	scheduleEntries,
	singleDefile,
	subscriptions
} from '../gallery/data';
import { json } from './api';

const HOUR_MS = 3_600_000;
const now = GALLERY_NOW.getTime();

/**
 * The festival in full swing at GALLERY_NOW: an event on stage, voting open with a
 * cast vote, quest standings and two unread notifications. The README gallery
 * captures it, and the a11y and tap-target specs scan it, because the stacked
 * state tints (current event, own vote, own leaderboard row) only appear here.
 * Pin the clock (`page.clock.setFixedTime(GALLERY_NOW)`) and layer a persona.
 */
export const festivalInProgress: Handlers = {
	'GET /config': json({
		festival_start: new Date(now - 2 * HOUR_MS).toISOString(),
		festival_end: new Date(now + 6 * HOUR_MS).toISOString(),
		quest_enabled: true,
		quest_max_award: 100
	}),
	'GET /notifications/unread-count': json({ count: 2 }),
	'GET /voting/status': json({
		can_vote: true,
		status: 'open',
		voting_start: new Date(now - HOUR_MS).toISOString(),
		voting_end: new Date(now + 4 * HOUR_MS).toISOString()
	}),
	'GET /schedule/': json({ schedule: scheduleEntries }),
	'GET /schedule/subscriptions/': json({ subscriptions }),
	'GET /voting/nominations/single': json(singleDefile),
	'GET /notifications/': json({ notifications, next_cursor: null }),
	'GET /quest': json(questStanding)
};
