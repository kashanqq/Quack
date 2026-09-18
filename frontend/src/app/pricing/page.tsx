import type { Metadata } from "next";
import { copy } from "@/components/home/copy";
import { CursorAura } from "@/components/home/CursorAura";
import { PricingPlans } from "@/components/home/PricingPlans";
import { SiteFooter } from "@/components/home/SiteFooter";
import { SiteHeader } from "@/components/home/SiteHeader";
import styles from "@/components/home/home.module.css";
import pricing from "@/components/home/pricing.module.css";

export const metadata: Metadata = {
  title: "Подписки — Quack!",
};

export default function PricingPage() {
  const t = copy.pricing;

  return (
    <div id="top" className={styles.page}>
      <CursorAura />

      <div className={styles.content}>
        <SiteHeader />

        <main className={pricing.main}>
          <h1 className={pricing.heading}>{t.heading}</h1>
          <p className={pricing.lead}>{t.lead}</p>
          <PricingPlans />
        </main>

        <SiteFooter />
      </div>
    </div>
  );
}
