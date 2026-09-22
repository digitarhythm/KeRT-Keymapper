/*
 * KeRT-Keymapper service worker: cross-origin isolation (COOP/COEP) for the pthread build on GitHub
 * Pages, plus cache-first delivery of the content-hashed build files so that a repeat visit does not
 * download the 12 MB of wasm/data again.
 *
 * The isolation part is coi-serviceworker v0.1.7 by Guido Zuidhof and contributors (MIT, see
 * coi-serviceworker.LICENSE), rewritten unminified; the caching part is ours.
 */
const CACHE_NAME = "kert-keymapper-assets-v2";
// main-<sha256>.wasm / .data / .js / .worker.js and datafile_main-<sha256>.data: the hash changes
// whenever the content does, so a cached copy can be served forever
const HASHED_ASSET = /\/(datafile_)?main-[0-9a-f]{64}\.(wasm|data|js|worker\.js)$/;

let coepCredentialless = false;

if (typeof window === "undefined") {
    // ---- service worker context ----
    self.addEventListener("install", () => self.skipWaiting());
    self.addEventListener("activate", (event) => event.waitUntil(
        caches.keys()
            .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
            .then(() => self.clients.claim())
    ));

    self.addEventListener("message", (event) => {
        if (!event.data) return;
        if (event.data.type === "deregister") {
            self.registration.unregister()
                .then(() => self.clients.matchAll())
                .then((clients) => clients.forEach((client) => client.navigate(client.url)));
        } else if (event.data.type === "coepCredentialless") {
            coepCredentialless = event.data.value;
        }
    });

    function withIsolationHeaders(response) {
        if (response.status === 0) return response;
        const headers = new Headers(response.headers);
        headers.set("Cross-Origin-Embedder-Policy", coepCredentialless ? "credentialless" : "require-corp");
        if (!coepCredentialless) headers.set("Cross-Origin-Resource-Policy", "cross-origin");
        headers.set("Cross-Origin-Opener-Policy", "same-origin");
        return new Response(response.body, {status: response.status, statusText: response.statusText, headers});
    }

    self.addEventListener("fetch", (event) => {
        const request = event.request;
        if (request.cache === "only-if-cached" && request.mode !== "same-origin") return;
        const outgoing = coepCredentialless && request.mode === "no-cors"
            ? new Request(request, {credentials: "omit"}) : request;

        if (request.method === "GET" && HASHED_ASSET.test(new URL(request.url).pathname)) {
            event.respondWith(caches.open(CACHE_NAME).then((cache) =>
                cache.match(request).then((cached) => {
                    if (cached) return withIsolationHeaders(cached);
                    return fetch(outgoing).then((response) => {
                        if (response.ok) cache.put(request, response.clone());
                        return withIsolationHeaders(response);
                    });
                })
            ).catch((e) => console.error(e)));
            return;
        }

        event.respondWith(fetch(outgoing).then(withIsolationHeaders).catch((e) => console.error(e)));
    });
} else {
    // ---- window context: register this file as the service worker and reload once it controls the page ----
    (() => {
        const reloadedBySelf = window.sessionStorage.getItem("coiReloadedBySelf");
        window.sessionStorage.removeItem("coiReloadedBySelf");
        const coepDegrading = reloadedBySelf == "coepdegrade";

        const coi = {
            shouldRegister: () => !reloadedBySelf,
            shouldDeregister: () => false,
            coepCredentialless: () => true,
            coepDegrade: () => true,
            doReload: () => window.location.reload(),
            quiet: false,
            ...window.coi
        };

        const n = navigator;
        const controlling = n.serviceWorker && n.serviceWorker.controller;

        if (controlling && !window.crossOriginIsolated) {
            window.sessionStorage.setItem("coiCoepHasFailed", "true");
        }
        const coepHasFailed = window.sessionStorage.getItem("coiCoepHasFailed");

        if (controlling) {
            const reloadToDegrade = coi.coepDegrade() && !(coepDegrading || window.crossOriginIsolated);
            n.serviceWorker.controller.postMessage({
                type: "coepCredentialless",
                value: (reloadToDegrade || (coepHasFailed && coi.coepDegrade())) ? false : coi.coepCredentialless(),
            });
            if (reloadToDegrade) {
                !coi.quiet && console.log("Reloading page to degrade COEP.");
                window.sessionStorage.setItem("coiReloadedBySelf", "coepdegrade");
                coi.doReload("coepdegrade");
            }
            if (coi.shouldDeregister()) {
                n.serviceWorker.controller.postMessage({type: "deregister"});
            }
        }

        if (window.crossOriginIsolated !== false || !coi.shouldRegister()) return;

        if (!window.isSecureContext) {
            !coi.quiet && console.log("COOP/COEP Service Worker not registered, a secure context is required.");
            return;
        }
        if (!n.serviceWorker) {
            !coi.quiet && console.error("COOP/COEP Service Worker not registered, perhaps due to private mode.");
            return;
        }
        n.serviceWorker.register(window.document.currentScript.src).then(
            (registration) => {
                !coi.quiet && console.log("COOP/COEP Service Worker registered", registration.scope);
                registration.addEventListener("updatefound", () => {
                    !coi.quiet && console.log("Reloading page to make use of updated COOP/COEP Service Worker.");
                    window.sessionStorage.setItem("coiReloadedBySelf", "updatefound");
                    coi.doReload();
                });
                if (registration.active && !n.serviceWorker.controller) {
                    !coi.quiet && console.log("Reloading page to make use of COOP/COEP Service Worker.");
                    window.sessionStorage.setItem("coiReloadedBySelf", "notcontrolling");
                    coi.doReload();
                }
            },
            (err) => { !coi.quiet && console.error("COOP/COEP Service Worker failed to register:", err); }
        );
    })();
}
