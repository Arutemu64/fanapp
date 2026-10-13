import type { QueryClient } from '@tanstack/vue-query';
import type { RouteLocationNormalized, RouteLocationRaw } from 'vue-router';

import type { BackTarget, NavbarAction } from '#lib/types/navigation.js';

/**
 * What a route's loader publishes for its page and for the shell around it: the
 * navbar heading, back arrow and action buttons, plus anything the page itself
 * needs that is worth waiting for before it is shown. Read with `usePageData()`.
 */
export interface PageData {
	/** Page heading rendered in the navbar. */
	title?: string;
	/** `document.title` when it should differ from `«<title> · ФАН ФАН»`. */
	documentTitle?: string;
	/** Parent route for the navbar's back arrow. */
	back?: BackTarget;
	/** Icon buttons beside the bell. */
	actions?: NavbarAction[];
	[key: string]: unknown;
}

/** An error the shell renders instead of the page. */
export interface ShownError {
	status: number;
	message: string;
	code?: string;
	/** Reference for a reported unexpected error, shown so a user can quote it. */
	errorId?: string;
}

export interface LoadContext {
	to: RouteLocationNormalized;
	queryClient: QueryClient;
	/** The data the loaders of the parent route records returned, merged — the `parent()` of a layout load. */
	parent: PageData;
}

/**
 * A route loader, run by the router before the navigation commits (see
 * `src/router/index.ts`). It guards (throw `redirect` / `error`), prefetches
 * (start a query, do not await it) and returns the page's data. Child loaders
 * run after their parents', in order.
 */
export type RouteLoader = (context: LoadContext) => PageData | void | Promise<PageData | void>;

/** An expected failure a loader reports; the shell renders it as an error screen. */
export class HttpError extends Error {
	readonly status: number;
	readonly code?: string;

	constructor(status: number, message: string, code?: string) {
		super(message);
		this.name = 'HttpError';
		this.status = status;
		this.code = code;
	}
}

/** Thrown by `redirect`; the router turns it into a redirect instead of an error. */
export class Redirect {
	constructor(readonly location: RouteLocationRaw) {}
}

export function error(status: number, message: string, code?: string): never {
	throw new HttpError(status, message, code);
}

export function redirect(location: RouteLocationRaw): never {
	throw new Redirect(location);
}

/** Identity helper that types a loader at its definition site. */
export function defineLoad<T extends PageData | void>(
	loader: (context: LoadContext) => T | Promise<T>
): (context: LoadContext) => T | Promise<T> {
	return loader;
}

/**
 * Attach a loader without pulling its code (and the query options it imports)
 * into the main chunk: the module is fetched on the first navigation to the route.
 */
export function lazyLoad(importer: () => Promise<{ load: RouteLoader }>): RouteLoader {
	return async (context) => (await importer()).load(context);
}
