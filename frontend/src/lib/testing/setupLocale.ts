import '#lib/i18n/locale.js';
import { setLocale } from '#lib/paraglide/runtime.js';

// Tests assert the Russian copy; without this the locale follows the Node
// runtime's `navigator.languages` (English) and every message would flip.
void setLocale('ru', { reload: false });
