/**
 * Generate out/precache.json from the real build output.
 *
 * The service worker installs *during* the first page load, so the HTML, CSS and JS
 * requested by that load are fetched before the worker controls the page and never pass
 * through its fetch handler -- meaning they never get cached. On a later offline visit
 * the shell would load unstyled, or not at all.
 *
 * Listing the built assets here lets the worker cache them explicitly at install. The
 * filenames are content-hashed and change every build, so this has to be generated after
 * `next build` rather than hand-written.
 */
import { readdirSync, statSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";

const OUT = "out";
const INCLUDE = /\.(css|js|jpg|jpeg|png|svg|webp|ico|json)$/;
// Source maps and the manifest we are writing are not needed offline.
const EXCLUDE = /\.map$|precache\.json$/;

function walk(dir) {
  return readdirSync(dir).flatMap((entry) => {
    const full = join(dir, entry);
    return statSync(full).isDirectory() ? walk(full) : [full];
  });
}

const files = walk(OUT);

const assets = files
  .filter((f) => INCLUDE.test(f) && !EXCLUDE.test(f))
  .map((f) => "/" + relative(OUT, f).split(/[\\/]/).join("/"));

// Each per-product page must be cached under the URL it is *served* at
// ("/price/dasani-15l"), not its file path ("/price/dasani-15l.html") -- the service
// worker matches on request URL, so caching the filename would never hit and the page
// would fail offline.
const routes = files
  .filter((f) => f.endsWith(".html") && !f.endsWith("404.html"))
  .map((f) => "/" + relative(OUT, f).split(/[\\/]/).join("/").replace(/\.html$/, ""))
  .map((route) => (route === "/index" ? "/" : route));

// Only the slashless form. A Next export also writes a price/x/ DIRECTORY of RSC
// payloads, so precaching "/price/x/" can store a directory response instead of the page.
// The service worker normalises trailing slashes when matching, which covers hosts that
// canonicalise the other way.
const precache = [...new Set(["/", ...assets, ...routes])].sort();

writeFileSync(join(OUT, "precache.json"), JSON.stringify(precache, null, 2) + "\n");
console.log(`precache manifest: ${precache.length} assets`);
