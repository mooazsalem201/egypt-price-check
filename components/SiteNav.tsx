"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/", label: "Prices" },
  { href: "/feedback", label: "Feedback" },
];

/**
 * Two-tab navigation, shown on every page.
 *
 * Deliberately plain links rather than a router-driven tab widget: the site is a static
 * export and every destination is a real page, so ordinary anchors keep it working with
 * no JavaScript and let the browser handle back/forward.
 */
export default function SiteNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Sections"
      className="border-b border-slate-200 bg-white/80 backdrop-blur dark:border-slate-700 dark:bg-slate-900/80"
    >
      <div className="mx-auto flex max-w-2xl gap-1 px-4">
        {TABS.map((tab) => {
          // "/" must match exactly, or it would light up on every product page too.
          const active =
            tab.href === "/" ? pathname === "/" : pathname.startsWith(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              aria-current={active ? "page" : undefined}
              className={`border-b-2 px-4 py-3 text-sm font-semibold transition ${
                active
                  ? "border-sky-600 text-sky-700 dark:border-sky-400 dark:text-sky-400"
                  : "border-transparent text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
