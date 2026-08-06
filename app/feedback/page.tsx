import type { Metadata } from "next";
import { absolute, SITE_NAME } from "@/lib/site";

const EMAIL = "mooazsalem2002@gmail.com";

export const metadata: Metadata = {
  title: "Feedback and corrections",
  description:
    "Report a wrong price, suggest a product to add, or send a suggestion for Egypt Price Check.",
  alternates: { canonical: absolute("/feedback") },
  openGraph: {
    title: `Feedback — ${SITE_NAME}`,
    description: "Report a wrong price, suggest a product, or send a suggestion.",
    url: absolute("/feedback"),
  },
};

/**
 * Pre-filled subjects and bodies, one per kind of message.
 *
 * A blank mailto puts the whole burden on the sender, who then writes "the price is wrong"
 * with no indication of which product, where, or what they actually paid -- which is
 * unactionable. The templates ask for the three things that make a report usable.
 */
const TOPICS = [
  {
    title: "A price looks wrong",
    blurb:
      "The most useful thing you can send. Prices are scraped from Egyptian supermarkets, so they can lag reality or pick the wrong pack size.",
    subject: "Wrong price on Egypt Price Check",
    body: [
      "Product:",
      "Price shown on the site:",
      "Price you actually saw:",
      "Where (shop and area):",
      "",
    ].join("\n"),
    tone: "border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950",
  },
  {
    title: "Add a product",
    blurb: "Something tourists buy that isn't listed yet.",
    subject: "Product suggestion for Egypt Price Check",
    body: ["Product and brand:", "Size:", "Where you usually see it:", ""].join("\n"),
    tone: "border-sky-300 bg-sky-50 dark:border-sky-700 dark:bg-sky-950",
  },
  {
    title: "Something is broken",
    blurb: "A page that won't load, a link that goes nowhere, a photo that's wrong.",
    subject: "Bug report — Egypt Price Check",
    body: ["What happened:", "Page or product:", "Phone and browser:", ""].join("\n"),
    tone: "border-rose-300 bg-rose-50 dark:border-rose-700 dark:bg-rose-950",
  },
  {
    title: "Suggestion or complaint",
    blurb: "Anything else — how it works, what's missing, what's annoying.",
    subject: "Feedback on Egypt Price Check",
    body: "",
    tone: "border-slate-300 bg-slate-50 dark:border-slate-600 dark:bg-slate-800",
  },
];

function mailto(subject: string, body: string) {
  const query = new URLSearchParams({ subject, ...(body ? { body } : {}) });
  return `mailto:${EMAIL}?${query.toString().replace(/\+/g, "%20")}`;
}

export default function FeedbackPage() {
  return (
    <main className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="mx-auto max-w-2xl px-4 pb-16 pt-6">
        <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-slate-50">
          Tell me what&rsquo;s wrong
        </h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          This site is one person checking supermarket prices. If something is out of date,
          missing, or plainly wrong, saying so is the fastest way it gets fixed.
        </p>

        <div className="mt-6 space-y-3">
          {TOPICS.map((topic) => (
            <a
              key={topic.title}
              href={mailto(topic.subject, topic.body)}
              className={`block rounded-2xl border-2 p-4 transition hover:shadow-md ${topic.tone}`}
            >
              <h2 className="font-bold text-slate-900 dark:text-slate-50">
                {topic.title} <span aria-hidden="true">→</span>
              </h2>
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{topic.blurb}</p>
            </a>
          ))}
        </div>

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-50">
            Or just email directly
          </h2>
          <p className="mt-1 text-sm">
            <a
              href={`mailto:${EMAIL}`}
              className="font-medium text-sky-700 underline underline-offset-2 dark:text-sky-400"
            >
              {EMAIL}
            </a>
          </p>
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
            These links open your own email app. The site has no contact form, no accounts
            and no analytics — nothing you do here is recorded, and there is no server to
            record it on.
          </p>
        </section>

        <section className="mt-6 text-xs text-slate-500 dark:text-slate-400">
          <h2 className="mb-1 font-semibold">Where the prices come from</h2>
          <p>
            Baselines are scraped from Carrefour Egypt and cross-checked against Spinneys,
            Talabat Mart and Mahmoud El Far. Each price on a product card links to the shop
            listings it came from, so you can check any figure yourself. Regional markups
            outside Cairo and the North Coast are estimates and are labelled as such.
          </p>
        </section>
      </div>
    </main>
  );
}
