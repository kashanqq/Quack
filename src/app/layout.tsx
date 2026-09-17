import type { Metadata } from "next";
import { Inter, Intel_One_Mono, Khula, Montserrat_Alternates, Raleway } from "next/font/google";
import { FlyingDucks } from "@/components/duck/FlyingDucks";
import { TransitionProvider } from "@/components/transition/TransitionProvider";
import "./globals.css";

const intelOneMono = Intel_One_Mono({ subsets: ["latin"], variable: "--font-intel-one-mono" });
const raleway = Raleway({ subsets: ["latin", "cyrillic"], variable: "--font-raleway" });
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const khula = Khula({ weight: "400", subsets: ["latin"], variable: "--font-khula" });
const montserratAlternates = Montserrat_Alternates({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-montserrat-alternates",
});

export const metadata: Metadata = {
  title: "Quack!",
  description: "Your companion for finding the right university and building a study plan to get in.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const fontVariables = [intelOneMono, raleway, inter, khula, montserratAlternates].map((f) => f.variable).join(" ");

  return (
    <html lang="ru" className={fontVariables}>
      <body>
        <TransitionProvider>
          {children}
          <FlyingDucks />
        </TransitionProvider>
      </body>
    </html>
  );
}
