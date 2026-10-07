import { removeStorage } from './safeStorage';

/**
 * Drop what the offline-capable builds stored on this device: the IndexedDB
 * cache of API data (per-user entries included, which must not linger on a
 * shared device) and the queued offline-logout flag. Both are dead weight now
 * that every read goes to the network. Best-effort: a browser that blocks
 * storage has nothing to delete.
 *
 * TODO: delete once every installed client has opened a build that runs this —
 * kept while the event's attendees may still open an install from before.
 */
export function purgeLegacyOfflineStorage(): void {
	removeStorage('local', 'fanfan:pending-logout');
	try {
		indexedDB.deleteDatabase('fanfan-cache');
	} catch {
		// Storage disabled (private modes, enterprise policy) — nothing to purge.
	}
}
