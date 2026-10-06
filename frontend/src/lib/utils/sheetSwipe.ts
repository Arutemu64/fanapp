// Below Tailwind's `sm`, where dialog-content.svelte lays a Dialog out as a bottom sheet.
const PHONE_QUERY = '(width < 40rem)';
// Movement before a touch counts as a drag, so a tap or a jittery press stays a tap.
const DRAG_SLOP_PX = 8;
// Released past this share of the sheet's height, or flicked faster than this, it closes.
const DISMISS_DISTANCE_RATIO = 0.25;
const DISMISS_VELOCITY_PX_PER_MS = 0.5;
const SNAP_BACK = 'transform 200ms cubic-bezier(0.32, 0.72, 0, 1)';

function isTextEntry(target: EventTarget | null): boolean {
	return target instanceof Element && target.closest('input, textarea, [contenteditable]') !== null;
}

/**
 * Swipe-down-to-dismiss for a bottom sheet, the gesture every native sheet has.
 * A downward drag that starts with the sheet scrolled to its top moves the sheet
 * instead of its content; any other gesture (scrolling the content, a sideways
 * swipe, a press in a text field) is left to the browser.
 *
 * Touch events rather than pointer events: the move must be cancelled to stop the
 * browser scrolling under the finger, and once a touch pans, pointer events only
 * deliver `pointercancel`. That needs a non-passive `touchmove`, so it is bound
 * on the sheet alone, never on the document.
 *
 * Returns a cleanup that unbinds everything.
 */
export function sheetSwipeToDismiss(sheet: HTMLElement, dismiss: () => void): () => void {
	const phone = window.matchMedia(PHONE_QUERY);
	let tracking = false;
	let dragging = false;
	let startX = 0;
	let startY = 0;
	let startTime = 0;
	let offset = 0;

	function snapBack() {
		sheet.style.transition = SNAP_BACK;
		sheet.style.transform = '';
		sheet.addEventListener('transitionend', () => sheet.style.removeProperty('transition'), {
			once: true
		});
	}

	function onTouchStart(event: TouchEvent) {
		tracking = false;
		const touch = event.touches[0];
		if (!touch || event.touches.length !== 1 || !phone.matches) return;
		if (sheet.scrollTop > 0 || isTextEntry(event.target)) return;
		tracking = true;
		dragging = false;
		startX = touch.clientX;
		startY = touch.clientY;
		startTime = event.timeStamp;
		offset = 0;
	}

	function onTouchMove(event: TouchEvent) {
		const touch = event.touches[0];
		if (!tracking || !touch) return;
		const dx = touch.clientX - startX;
		const dy = touch.clientY - startY;

		if (!dragging) {
			if (Math.abs(dx) < DRAG_SLOP_PX && Math.abs(dy) < DRAG_SLOP_PX) return;
			const pullsDown = dy > 0 && Math.abs(dy) > Math.abs(dx);
			if (!pullsDown) {
				tracking = false;
				return;
			}
			dragging = true;
			sheet.style.transition = 'none';
		}

		event.preventDefault();
		offset = Math.max(0, dy);
		sheet.style.transform = `translateY(${offset}px)`;
	}

	function onTouchEnd(event: TouchEvent) {
		if (!dragging) {
			tracking = false;
			return;
		}
		tracking = false;
		dragging = false;

		const elapsed = Math.max(1, event.timeStamp - startTime);
		const farEnough = offset > sheet.offsetHeight * DISMISS_DISTANCE_RATIO;
		const fastEnough = offset / elapsed > DISMISS_VELOCITY_PX_PER_MS;
		if (farEnough || fastEnough) {
			// The dialog's exit animation has only a `to` keyframe, so it slides on from
			// the dragged offset instead of jumping back first.
			sheet.style.removeProperty('transition');
			dismiss();
			return;
		}
		snapBack();
	}

	function onTouchCancel() {
		if (dragging) snapBack();
		tracking = false;
		dragging = false;
	}

	sheet.addEventListener('touchstart', onTouchStart, { passive: true });
	sheet.addEventListener('touchmove', onTouchMove, { passive: false });
	sheet.addEventListener('touchend', onTouchEnd);
	sheet.addEventListener('touchcancel', onTouchCancel);

	return () => {
		sheet.removeEventListener('touchstart', onTouchStart);
		sheet.removeEventListener('touchmove', onTouchMove);
		sheet.removeEventListener('touchend', onTouchEnd);
		sheet.removeEventListener('touchcancel', onTouchCancel);
	};
}
