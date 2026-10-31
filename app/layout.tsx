import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "Ciccio — il tuo assistente", description: "Uno spazio privato per ragionare, ricordare e costruire insieme." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="it"><body>{children}</body></html>; }
