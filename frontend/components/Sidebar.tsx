"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, Users, User, Settings, LogOut, Camera } from "lucide-react";
import { clsx } from "clsx";

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const [userRole, setUserRole] = useState<string>("student");

  useEffect(() => {
    if (typeof window !== "undefined") {
      setUserRole(localStorage.getItem("role") || "student");
    }
  }, []);

  let links = [
    { name: "My Dashboard", href: "/", icon: Camera, visibleFor: ["student"] },
    { name: "Live Scanner", href: "/", icon: Camera, visibleFor: ["teacher", "admin"] },
    { name: "Teacher Dashboard", href: "/teacher", icon: LayoutDashboard, visibleFor: ["teacher", "admin"] },
    { name: "Students", href: "/students", icon: Users, visibleFor: ["teacher", "admin"] },
    { name: "Settings", href: "/settings", icon: Settings, visibleFor: ["admin"] },
  ].filter(link => link.visibleFor.includes(userRole));

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("role");
    localStorage.removeItem("branch");
    router.push("/login");
  };

  return (
    <aside className="w-64 glass h-screen fixed left-0 top-0 flex flex-col pt-6 pb-4">
      <div className="px-6 mb-8 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/30">
          <Camera className="text-white w-6 h-6" />
        </div>
        <h1 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-100 to-blue-400">
          AI Attendance
        </h1>
      </div>
      
      <nav className="flex-1 px-4 space-y-2">
        {links.map((link) => {
          const Icon = link.icon;
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.name}
              href={link.href}
              className={clsx(
                "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 ease-in-out group",
                isActive 
                  ? "bg-blue-600/20 text-blue-400 shadow-inner" 
                  : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/50"
              )}
            >
              <Icon className={clsx("w-5 h-5", isActive ? "text-blue-400" : "text-slate-400 group-hover:text-blue-300 transition-colors")} />
              <span className="font-medium text-sm">{link.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-4 mt-auto">
        <button 
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all duration-300"
        >
          <LogOut className="w-5 h-5" />
          <span className="font-medium text-sm">Logout</span>
        </button>
      </div>
    </aside>
  );
}
