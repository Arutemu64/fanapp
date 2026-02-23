export type ToastColor = 'green' | 'red' | 'yellow' | 'blue';
export type ToastType = 'success' | 'info' | 'warning' | 'error';

export const ToastTypeColors: Record<ToastType, ToastColor> = {
	success: 'green',
	info: 'blue',
	warning: 'yellow',
	error: 'red'
};

export interface ToastItem {
	id: number;
	message: string;
	type: ToastType;
}

// Private state within the module
let toasts = $state<ToastItem[]>([]);

export const toastService = {
	// Getter to access the state reactively
	get items() {
		return toasts;
	},

	add(message: string, type: ToastType = 'info') {
		const id = Date.now();
		const newToast: ToastItem = { id, message, type };

		toasts.push(newToast);

		// Auto-dismiss after 5 seconds
		setTimeout(() => {
			this.dismiss(id);
		}, 5000);
	},

	error(err: unknown) {
		let message = 'Произошла ошибка';

		// Handle string directly
		if (typeof err === 'string') {
			message = err;
		}
		// Handle openapi-fetch error response body
		else if (err && typeof err === 'object') {
			// Check for HTTPValidationError format (detail array)
			if ('detail' in err && Array.isArray(err.detail) && err.detail.length > 0) {
				// Extract first validation error message
				message = err.detail[0].msg;
			}
			// Check for simple detail string
			else if ('detail' in err && typeof err.detail === 'string') {
				message = err.detail;
			}
		}
		// Fallback to standard Error
		else if (err instanceof Error) {
			message = err.message;
		}

		this.add(message, 'error');
	},

	dismiss(id: number) {
		toasts = toasts.filter((t) => t.id !== id);
	}
};
