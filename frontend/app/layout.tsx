import type { Metadata } from "next";
import "./globals.css";
import localFont from "next/font/local";
const displayFont = localFont({
  src: "./fonts/hackamatch-display.woff",
  variable: "--font-display",
  weight: "800",
  display: "swap",
});
export const metadata: Metadata = {
  title: "HackAMatch · Find your three",
  description:
    "Data Mavericks × NSDC. Verified registrations. Complementary skills. Teams built to build.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={displayFont.variable}>
      <body>{children}</body>
    </html>
  );
}
