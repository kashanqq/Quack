"use client";

import Link from "next/link";
import type { ComponentProps } from "react";
import { usePageTransition } from "./TransitionProvider";

type TransitionLinkProps = Omit<ComponentProps<typeof Link>, "href"> & { href: string };

/** A Next.js link that shows the duck loader before switching pages. */
export function TransitionLink({ href, onClick, ...props }: TransitionLinkProps) {
  const { navigate } = usePageTransition();

  return (
    <Link
      href={href}
      {...props}
      onClick={(e) => {
        onClick?.(e);
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        if (props.target === "_blank") return;
        e.preventDefault();
        navigate(href);
      }}
    />
  );
}
