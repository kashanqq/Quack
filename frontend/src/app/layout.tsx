import type { Metadata } from "next";
import { Inter, Intel_One_Mono, Raleway } from "next/font/google";
import { ScrollToTopOnReload } from "@/components/ScrollToTopOnReload";
import { TransitionProvider } from "@/components/transition/TransitionProvider";
import "./globals.css";

const intelOneMono = Intel_One_Mono({ subsets: ["latin"], variable: "--font-intel-one-mono" });
const raleway = Raleway({ subsets: ["latin", "cyrillic"], variable: "--font-raleway" });
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Quack!",
  description: "Your companion for finding the right university and building a study plan to get in.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const fontVariables = [intelOneMono, raleway, inter].map((f) => f.variable).join(" ");

  return (
    <html lang="ru" className={fontVariables}>
      <body>
        <ScrollToTopOnReload />
        <TransitionProvider>
          {children}
        </TransitionProvider>
      </body>
    </html>
  );
}
