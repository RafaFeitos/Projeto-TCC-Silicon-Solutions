import type { Metadata } from "next";
import "./global.css";

export const metadata: Metadata = {
  title: "Industrial Monitor — Monitoramento de Máquinas",
  description: "dashboard de monitoramento preditivo para máquinas legadas",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}