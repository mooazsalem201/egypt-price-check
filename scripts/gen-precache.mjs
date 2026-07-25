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

const assets = walk(OUT)
  .filter((f) => INCLUDE.test(f) && !EXCLUDE.test(f))
  .map((f) => "/" + relative(OUT, f).split(/[\\/]/).join("/"));

// "/" covers the app shell; Next serves index.html from it.
const precache = ["/", ...assets].sort();

writeFileSync(join(OUT, "precache.json"), JSON.stringify(precache, null, 2) + "\n");
console.log(`precache manifest: ${precache.length} assets`);
