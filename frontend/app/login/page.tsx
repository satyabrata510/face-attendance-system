"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Lock, User, Eye, EyeOff, ShieldCheck, ArrowRight } from "lucide-react";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const res = await fetch("http://localhost:8000/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username, password }),
      });

      if (res.ok) {
        const data = await res.json();
        localStorage.setItem("access_token", data.access_token);
        if (data.role) localStorage.setItem("role", data.role);
        if (data.branch) localStorage.setItem("branch", data.branch);
        if (data.student_id) localStorage.setItem("student_id", data.student_id);
        
        // Wait briefly for a nice UI state sequence
        setTimeout(() => {
          router.push("/");
        }, 600);
      } else {
        const data = await res.json();
        setError(data.detail || "Invalid credentials. Please try again.");
        setIsLoading(false);
      }
    } catch (err) {
      setError("Failed to connect to the server. Please ensure backend is running.");
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full flex items-center justify-center relative z-10 w-full max-w-7xl mx-auto h-[100vh]">
      {/* Background Ambience */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-blue-600/20 blur-[120px] rounded-full pointer-events-none opacity-50 animate-pulse-slow"></div>
      
      <div className="w-full max-w-md animate-in fade-in zoom-in-95 duration-700 ease-out z-10">
        
        {/* Header Icon */}
        <div className="flex justify-center mb-8">
          <div className="relative">
            <div className="absolute inset-0 bg-blue-500 blur-xl opacity-40 rounded-full"></div>
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-tr from-blue-600 to-cyan-400 flex items-center justify-center shadow-2xl relative border border-white/10 glass-highlight">
              <ShieldCheck className="w-10 h-10 text-white" strokeWidth={1.5} />
            </div>
          </div>
        </div>

        {/* Login Card */}
        <div className="glass-card bg-[#0A0F1F]/60 backdrop-blur-xl border border-white/5 rounded-[2rem] p-8 shadow-2xl relative overflow-hidden">
          {/* Subtle top edge gradient */}
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-blue-400/50 to-transparent"></div>
          
          <div className="text-center mb-10">
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-blue-200 tracking-tight">System Gateway</h1>
            <p className="text-slate-400 mt-2 text-sm font-medium">Log in as Student, Teacher, or Admin</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-6">
            
            {/* Username Field */}
            <div className="space-y-2">
              <label className="text-[13px] font-semibold text-blue-200/80 ml-1 uppercase tracking-wider">Username / Registration No</label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none text-slate-500 group-focus-within:text-blue-400 transition-colors">
                  <User className="w-5 h-5" />
                </div>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-[#030712]/50 border border-slate-800 rounded-xl py-4 pl-12 pr-4 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all text-[15px]"
                  placeholder="Enter username or registration no"
                  autoComplete="off"
                  required
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-2">
              <label className="text-[13px] font-semibold text-blue-200/80 ml-1 uppercase tracking-wider">Password</label>
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none text-slate-500 group-focus-within:text-blue-400 transition-colors">
                  <Lock className="w-5 h-5" />
                </div>
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-[#030712]/50 border border-slate-800 rounded-xl py-4 pl-12 pr-12 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 transition-all text-[15px]"
                  placeholder="Enter your secure password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 flex items-center pr-4 text-slate-500 hover:text-blue-400 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl animate-in shake">
                <p className="text-[13px] text-red-400/90 text-center font-medium">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className={`w-full py-4 rounded-xl font-bold text-white shadow-lg transition-all duration-300 relative overflow-hidden group ${
                isLoading 
                  ? "bg-slate-800 cursor-not-allowed" 
                  : "bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 hover:shadow-blue-500/25 hover:-translate-y-0.5"
              }`}
            >
              <div className="absolute inset-0 w-full h-full bg-white/20 scale-x-0 group-hover:scale-x-100 origin-left transition-transform duration-500 ease-out z-0"></div>
              <span className="relative z-10 flex items-center justify-center gap-2">
                {isLoading ? (
                  <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    Authenticate <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </>
                )}
              </span>
            </button>
            
          </form>
          
          <div className="mt-8 text-center">
            <div className="flex items-center justify-center gap-2 text-slate-500 text-sm">
              <ShieldCheck className="w-4 h-4" />
              <span>Protected by high-grade encryption</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
