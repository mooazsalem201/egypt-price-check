"use client";

import { useEffect, useRef } from "react";

interface Props {
  src: string;
  alt: string;
}

/**
 * Product photo that opens full size on tap.
 *
 * The thumbnail is 96px, which is enough to recognise a familiar wrapper but not enough
 * to read a brand off a narrow bottle. The stored images are 400px, so there is real
 * detail to show; without a way to enlarge it that detail is simply wasted.
 *
 * Uses a native <dialog> so focus trapping, Escape-to-close and the top layer come from
 * the browser rather than being reimplemented badly.
 */
export default function ProductImage({ src, alt }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  // Clicking the backdrop should close it, but the backdrop is not a separate element --
  // a click outside the image's box still targets the dialog itself.
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const onClick = (event: MouseEvent) => {
      if (event.target === dialog) dialog.close();
    };
    dialog.addEventListener("click", onClick);
    return () => dialog.removeEventListener("click", onClick);
  }, []);

  return (
    <>
      <button
        type="button"
        onClick={() => dialogRef.current?.showModal()}
        aria-label={`Enlarge photo of ${alt}`}
        className="group relative shrink-0 rounded-lg ring-1 ring-slate-200 transition
                   hover:ring-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-500
                   dark:ring-slate-700"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={alt}
          width={96}
          height={96}
          loading="lazy"
          className="h-24 w-24 rounded-lg bg-white object-contain p-1.5"
        />
        <span
          aria-hidden="true"
          className="absolute bottom-1 right-1 rounded bg-slate-900/70 px-1 text-[10px]
                     font-medium leading-4 text-white opacity-80 group-hover:opacity-100"
        >
          ⤢
        </span>
      </button>

      <dialog
        ref={dialogRef}
        className="max-h-[90dvh] max-w-[90vw] rounded-2xl bg-white p-0 backdrop:bg-slate-900/70
                   dark:bg-slate-900"
      >
        <div className="flex flex-col items-center gap-3 p-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={src}
            alt={alt}
            className="max-h-[70dvh] w-auto max-w-full rounded-lg bg-white object-contain"
          />
          <p className="max-w-xs text-center text-sm text-slate-600 dark:text-slate-300">
            {alt}
          </p>
          <button
            type="button"
            onClick={() => dialogRef.current?.close()}
            className="rounded-full bg-slate-900 px-5 py-2.5 text-sm font-medium text-white
                       dark:bg-slate-100 dark:text-slate-900"
          >
            Close
          </button>
        </div>
      </dialog>
    </>
  );
}
