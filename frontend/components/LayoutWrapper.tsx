"use client";

import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import Header from "@/components/Header";

export default function LayoutWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  const isLoginPage = pathname === "/login";

  if (isLoginPage) {
    return <main className="min-h-screen z-0 relative flex items-center justify-center p-4 bg-[#030712]">{children}</main>;
  }

  return (
    <>
      <Sidebar />
      <Header />
      <main className="flex-1 ml-64 p-8 pt-8 z-0 relative">
        {children}
      </main>
    </>
  );
}
