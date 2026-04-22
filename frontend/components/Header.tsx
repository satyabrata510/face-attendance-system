"use client";

import { Bell, Search } from "lucide-react";

export default function Header() {
  return (
    <header className="glass h-20 w-full pl-64 pr-8 flex items-center justify-between border-b border-slate-800 z-10 sticky top-0">
      <div className="flex-1 ml-8 max-w-xl">
        <div className="relative group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 group-focus-within:text-blue-400 transition-colors" />
          <input 
            type="text" 
            placeholder="Search students, classes, or attendance records..." 
            className="w-full bg-slate-800/50 border border-slate-700 text-slate-200 placeholder:text-slate-500 rounded-2xl py-3 pl-12 pr-4 outline-none focus:border-blue-500/50 focus:bg-slate-800 focus:ring-4 ring-blue-500/10 transition-all duration-300"
          />
        </div>
      </div>
      
      <div className="flex items-center gap-6 ml-8">
        <button className="relative p-2 text-slate-400 hover:text-white transition-colors">
          <Bell className="w-6 h-6" />
          <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-blue-500 rounded-full border-2 border-slate-900"></span>
        </button>
        
        <div className="flex items-center gap-3 pl-6 border-l border-slate-800">
          <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold shadow-md">
            S
          </div>
          <div className="hidden md:block text-sm">
            <p className="font-semibold text-slate-200">Satya B.</p>
            <p className="text-slate-500 text-xs">Administrator</p>
          </div>
        </div>
      </div>
    </header>
  );
}
