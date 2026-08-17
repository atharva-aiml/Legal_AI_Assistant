import type { Metadata } from "next";
import { Source_Serif_4, Public_Sans, JetBrains_Mono } from "next/font/google";
import { ListSearchProvider } from "@/components/list-search-context";
import { ToastProvider } from "@/components/toast-context";
import "@/styles/globals.css";

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-heading",
  display: "swap",
});

const publicSans = Public_Sans({
  subsets: ["latin"],
  variable: "--font-ui",
  display: "swap",
});

const jetBrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Legal AI Assistant",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sourceSerif.variable} ${publicSans.variable} ${jetBrainsMono.variable}`}>
      <body>
        <ListSearchProvider>
          <ToastProvider>{children}</ToastProvider>
        </ListSearchProvider>
      </body>
    </html>
  );
}
