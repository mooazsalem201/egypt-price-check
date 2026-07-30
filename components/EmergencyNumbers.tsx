import emergency from "@/data/emergency.json";

/**
 * Useful numbers, always available at the foot of the page.
 *
 * Rendered as a <details> so it costs one line until opened, and as tel: links so a tap
 * dials. Static content, so it survives in the offline cache like everything else -- which
 * matters most, since the moment someone needs the tourism hotline is unlikely to be the
 * moment they have signal to search for it.
 */
export default function EmergencyNumbers() {
  return (
    <details className="mt-8 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <summary className="cursor-pointer text-sm font-semibold text-slate-900 dark:text-slate-50">
        Useful numbers in Egypt
      </summary>

      <div className="mt-3 space-y-4">
        {emergency.groups.map((group) => (
          <section key={group.title}>
            <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {group.title}
            </h3>
            <ul className="space-y-1.5">
              {group.entries.map((entry) => (
                <li
                  key={entry.label}
                  className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5"
                >
                  <span className="text-sm text-slate-700 dark:text-slate-300">
                    {entry.label}
                    {entry.note && (
                      <span className="block text-xs text-slate-400 dark:text-slate-500">
                        {entry.note}
                      </span>
                    )}
                  </span>
                  <a
                    href={`tel:${entry.dial}`}
                    className="ml-auto font-bold tabular-nums text-sky-700 underline
                               underline-offset-2 dark:text-sky-400"
                  >
                    {entry.number}
                  </a>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      <p className="mt-3 text-xs text-slate-400 dark:text-slate-500">{emergency.note}</p>
    </details>
  );
}
