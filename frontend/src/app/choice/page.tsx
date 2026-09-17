import type { Metadata } from "next";
import { ChoiceRoot } from "@/components/choice/ChoiceRoot";

export const metadata: Metadata = {
  title: "Quack! — Выбор",
};

export default function ChoicePage() {
  return <ChoiceRoot />;
}
