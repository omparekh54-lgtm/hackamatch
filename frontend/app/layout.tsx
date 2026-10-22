import type { Metadata } from "next";
import "./globals.css";
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
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
