import { type ClassValue, clsx } from 'clsx';
import { extendTailwindMerge } from 'tailwind-merge';

// Deviates from upstream: registers the type roles from app.css `@theme`. Unregistered,
// tailwind-merge reads `text-body` as a text colour and `cn('text-body text-foreground')`
// silently drops it.
const twMerge = extendTailwindMerge({
	extend: { theme: { text: ['headline', 'section', 'body'] } }
});

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

export type WithoutChild<T> = T extends { child?: unknown } ? Omit<T, 'child'> : T;
export type WithoutChildren<T> = T extends { children?: unknown } ? Omit<T, 'children'> : T;
export type WithoutChildrenOrChild<T> = WithoutChildren<WithoutChild<T>>;
export type WithElementRef<T, U extends HTMLElement = HTMLElement> = T & { ref?: U | null };
