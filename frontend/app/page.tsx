"use client";

import { ScanFace, UserCheck, Play, Camera, RefreshCw, AlertTriangle, User } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();
  const [isScanning, setIsScanning] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [stats, setStats] = useState({ totalActive: 0, accuracy: "99.8%" });
  const [recentAttendances, setRecentAttendances] = useState<any[]>([]);
  const [userRole, setUserRole] = useState<string>("");
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    async function init() {
      let token = localStorage.getItem("access_token");
      if (!token) {
        router.push("/login");
        return;
      }
      
      const role = localStorage.getItem("role") || "";
      const studentId = localStorage.getItem("student_id") || null;
      setUserRole(role);
      fetchStats(token, role, studentId);
    }
    
    init();
    return () => stopCamera();
  }, [router]);

  const [studentProfile, setStudentProfile] = useState<any>(null);

  const fetchStats = async (token: string, role: string, studentId: string | null) => {
    try {
      if (role === "student" && studentId) {
        const res = await fetch(`http://localhost:8000/api/reports/student/${studentId}`, { headers: { "Authorization": `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setStudentProfile(data);
          // Set stats.totalActive based on today's record if present, though we might not need it if we have the full profile
          const today = new Date().toISOString().split('T')[0];
          const todayRecord = data.records.find((r: any) => r.date.startsWith(today));
          setStats(prev => ({ ...prev, totalActive: todayRecord && ["Present", "Late"].includes(todayRecord.status) ? 1 : 0 }));
        }
      } else {
        const [todayRes, recentRes] = await Promise.all([
          fetch("http://localhost:8000/api/attendance/today", { headers: { "Authorization": `Bearer ${token}` } }),
          fetch("http://localhost:8000/api/attendance/recent?limit=10", { headers: { "Authorization": `Bearer ${token}` } })
        ]);
        
        if (todayRes.ok) {
          const todayData = await todayRes.json();
          setStats(prev => ({ ...prev, totalActive: todayData.present_count }));
        }
        if (recentRes.ok) {
          const recentData = await recentRes.json();
          setRecentAttendances(recentData);
        }
      }
    } catch (err) {}
  };

  const startCamera = async () => {
    try {
      setCameraError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      
      streamRef.current = stream;
      setIsScanning(true); // Mount the <video> element
      
      // Wait for React to render the <video> tag before attaching the stream
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = () => {
            videoRef.current?.play().catch(console.error);
          };
        }
      }, 100);
      
      const token = localStorage.getItem("access_token");
      if (token) {
        fetch("http://localhost:8000/api/attendance/clear-cooldown", {
          method: "POST",
          headers: { "Authorization": `Bearer ${token}` }
        });
      }

      intervalRef.current = setInterval(processFrame, 3000);
    } catch (err: any) {
      console.error("Camera access denied", err);
      let errMsg = "Camera access denied. Please ensure permissions are granted.";
      if(err.name === 'NotAllowedError') errMsg = "Camera access denied. Please allow camera permissions in your browser settings.";
      else if(err.name === 'NotFoundError') errMsg = "No camera found. Please connect a webcam.";
      setCameraError(errMsg);
      setIsScanning(false);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsScanning(false);
  };

  const processFrame = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      const formData = new FormData();
      formData.append("file", blob, "frame.jpg");
      
      try {
        const res = await fetch("http://localhost:8000/api/attendance/mark-by-face", {
          method: "POST",
          headers: { "Authorization": `Bearer ${token}` },
          body: formData
        });
        
        if (res.ok) {
          const data = await res.json();
          if (data.success && data.students && data.students.length > 0) {
            fetchStats(token);
          }
        }
      } catch (err) {}
    }, "image/jpeg", 0.8);
  };

  const toggleCamera = () => {
    if (isScanning) stopCamera();
    else startCamera();
  };

  return (
    <div className="max-w-7xl mx-auto animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out pb-10">
      
      {userRole === "student" ? (
        <div className="mb-8">
          <h1 className="text-[28px] font-bold text-white tracking-tight flex items-center gap-2">
            My Attendance
          </h1>
          <p className="text-slate-400 mt-1.5 text-[15px]">View your current attendance status</p>
        </div>
      ) : (
        <div className="mb-8">
          <h1 className="text-[28px] font-bold text-white tracking-tight flex items-center gap-2">
            Live Attendance Scanner
          </h1>
          <p className="text-slate-400 mt-1.5 text-[15px]">Use face recognition to automatically mark student attendance</p>
        </div>
      )}

      <div className={`grid grid-cols-1 ${userRole !== "student" ? "lg:grid-cols-[1.7fr_1fr]" : "max-w-2xl mx-auto"} gap-6`}>
        
        {/* Left Col: Camera Feed (HIDDEN FOR STUDENTS) */}
        {userRole !== "student" && (
          <div className="bg-[#0B1121] rounded-2xl border border-slate-800/80 p-6 flex flex-col shadow-lg">
            <h2 className="text-[17px] font-bold text-white mb-4">Camera Feed</h2>
          
          <div className="bg-[#030712] flex-1 rounded-xl border border-slate-800/80 min-h-[400px] relative overflow-hidden flex items-center justify-center mb-6">
            {isScanning ? (
              <>
                <video 
                  ref={videoRef} 
                  autoPlay 
                  playsInline 
                  muted 
                  className="absolute inset-0 w-full h-full object-cover z-0 scale-x-[-1]"
                />
                <canvas ref={canvasRef} className="hidden" />
                
                {/* Subtle overlay corners */}
                <div className="absolute inset-0 z-10 pointer-events-none p-6">
                  <div className="w-full h-full border-[2px] border-emerald-500/20 relative rounded-lg">
                    <div className="absolute top-0 left-0 w-8 h-8 border-t-4 border-l-4 border-emerald-500 rounded-tl-lg -translate-x-[2px] -translate-y-[2px]" />
                    <div className="absolute top-0 right-0 w-8 h-8 border-t-4 border-r-4 border-emerald-500 rounded-tr-lg translate-x-[2px] -translate-y-[2px]" />
                    <div className="absolute bottom-0 left-0 w-8 h-8 border-b-4 border-l-4 border-emerald-500 rounded-bl-lg -translate-x-[2px] translate-y-[2px]" />
                    <div className="absolute bottom-0 right-0 w-8 h-8 border-b-4 border-r-4 border-emerald-500 rounded-br-lg translate-x-[2px] translate-y-[2px]" />
                  </div>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center text-slate-500 w-full h-full">
                {cameraError ? (
                  <>
                    <AlertTriangle className="w-10 h-10 mb-3 text-amber-500 opacity-80" />
                    <p className="text-amber-400/90 text-sm max-w-[300px] text-center leading-relaxed">{cameraError}</p>
                  </>
                ) : (
                  <>
                    <Camera className="w-12 h-12 mb-3 text-slate-600/80 stroke-[1.5]" />
                    <p className="font-medium text-[15px] text-slate-400">Camera Inactive - Click Start to begin</p>
                  </>
                )}
              </div>
            )}
          </div>

          <button 
            onClick={toggleCamera}
            className={`w-full py-3.5 rounded-[14px] font-semibold transition-all duration-300 flex items-center justify-center gap-2 text-[15px] ${
              isScanning 
                ? "bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/30" 
                : "bg-[#10B981] hover:bg-[#059669] text-white"
            }`}
          >
            {isScanning ? (
              "Stop Camera"
            ) : (
              <>
                <Play className="w-[18px] h-[18px] fill-current" />
                Start Camera
              </>
            )}
          </button>
        </div>
        )}

        {/* Right Col: Stats and Instructions */}
        <div className="space-y-6 flex flex-col min-h-0">
          
          {/* Status / Present Today Panel */}
          <div className="bg-[#0B1121] rounded-2xl border border-slate-800/80 p-6 flex flex-col flex-1 min-h-[300px] shadow-lg">
            <div className="flex items-center justify-between mb-8">
              <div className="flex items-center gap-2">
                <UserCheck className={`w-5 h-5 ${userRole === "student" && stats.totalActive > 0 ? "text-[#10B981]" : userRole === "student" ? "text-amber-500" : "text-[#10B981]"}`} strokeWidth={2.5} />
                <h2 className="text-[16px] font-bold text-white">
                  {userRole === "student" ? "My Status Today" : "Present Today"}
                </h2>
                {userRole !== "student" && (
                  <span className="bg-[#10B981] text-white text-[11px] font-bold w-5 h-5 flex items-center justify-center rounded-full leading-none ml-1">
                    {stats.totalActive}
                  </span>
                )}
              </div>
              <button 
                onClick={() => fetchStats(localStorage.getItem("access_token") || "")}
                className="flex items-center gap-1.5 text-[13px] font-medium text-slate-400 hover:text-white transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Refresh
              </button>
            </div>
            
            {userRole === "student" ? (
              <div className="flex-1 flex flex-col p-2">
                {studentProfile ? (
                  <div className="space-y-6">
                    <div className="bg-slate-900/50 rounded-xl p-5 border border-slate-700/50 flex flex-col sm:flex-row gap-5 items-center sm:items-start text-center sm:text-left shadow-inner">
                      <div className="w-16 h-16 rounded-full bg-slate-800 border-2 border-slate-600 flex items-center justify-center flex-shrink-0 text-xl font-bold text-slate-400">
                        {studentProfile.student?.name?.charAt(0) || <User className="w-8 h-8" />}
                      </div>
                      <div className="flex-1">
                        <h3 className="text-xl font-bold text-white tracking-tight">{studentProfile.student?.name}</h3>
                        <p className="text-blue-400 font-mono text-sm mt-1">{studentProfile.student?.roll_no}</p>
                        <div className="flex flex-wrap gap-2 mt-3 justify-center sm:justify-start">
                          <span className="px-3 py-1 bg-slate-800 rounded-md text-xs font-semibold text-slate-300 border border-slate-700">
                            Branch: {studentProfile.student?.department}
                          </span>
                          <span className="px-3 py-1 bg-slate-800 rounded-md text-xs font-semibold text-slate-300 border border-slate-700">
                            Attendance: {studentProfile.stats?.attendance_rate}%
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex flex-col items-center justify-center text-center p-4 bg-slate-900/30 rounded-xl border border-slate-800">
                      <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 shadow-lg border-[3px] transition-all transform hover:scale-105 ${stats.totalActive > 0 ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                        {stats.totalActive > 0 ? (
                          <UserCheck className="w-8 h-8 text-emerald-500" />
                        ) : (
                          <AlertTriangle className="w-8 h-8 text-red-500" />
                        )}
                      </div>
                      <h4 className="text-[13px] font-semibold text-slate-400 uppercase tracking-wider mb-1">Today's System Status</h4>
                      <h3 className={`text-2xl font-bold ${stats.totalActive > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {stats.totalActive > 0 ? 'PRESENT' : 'ABSENT'}
                      </h3>
                      <p className="text-slate-500 mt-2 text-xs max-w-[250px]">
                        {stats.totalActive > 0 
                          ? "Your attendance was captured via face recognition." 
                          : "No record found. Please walk past the scanner."}
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 flex items-center justify-center">
                    <p className="text-slate-500 animate-pulse">Loading profile...</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {recentAttendances.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full pb-6 pt-4">
                    <div className="w-12 h-12 rounded-full border-[2px] border-slate-700 flex items-center justify-center mb-4">
                      <span className="text-xl font-bold text-slate-500">!</span>
                    </div>
                    <p className="font-medium text-slate-300 text-[15px]">No attendance marked yet</p>
                    <p className="text-slate-500 text-[13px] mt-1 text-center max-w-[200px]">Start the camera to detect faces</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {recentAttendances.map((record) => (
                      <div key={record.id} className="flex items-center gap-3 p-3 rounded-xl hover:bg-slate-800/30 transition-colors">
                        <div className="w-10 h-10 rounded-full bg-[#10B981]/10 flex items-center justify-center text-[#10B981]">
                          <UserCheck className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-[14px] font-medium text-white truncate">{record.name}</p>
                          <p className="text-[12px] text-slate-400 mt-0.5">Marked {record.status}</p>
                        </div>
                        <div className="text-[11px] font-medium text-slate-500 bg-slate-800/60 px-2 py-1 rounded-md">{record.time}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* How it works Panel (Hidden for Students) */}
          {userRole !== "student" && (
            <div className="bg-[#0B1121] rounded-2xl border border-slate-800/80 p-6 shadow-lg">
              <h3 className="text-[15px] font-semibold text-slate-200 mb-4 tracking-wide">How it works</h3>
              <div className="space-y-3">
                <div className="flex text-slate-400 text-[14px]">
                  <span className="w-6 text-slate-600 font-medium">1.</span>
                  <span>Click "Start Camera" to begin</span>
                </div>
                <div className="flex text-slate-400 text-[14px]">
                  <span className="w-6 text-slate-600 font-medium">2.</span>
                  <span>Look at the camera clearly</span>
                </div>
                <div className="flex text-slate-400 text-[14px]">
                  <span className="w-6 text-slate-600 font-medium">3.</span>
                  <span>System auto-detects registered faces</span>
                </div>
                <div className="flex text-slate-400 text-[14px]">
                  <span className="w-6 text-slate-600 font-medium">4.</span>
                  <span>Attendance is marked automatically</span>
                </div>
                <div className="flex text-slate-400 text-[14px]">
                  <span className="w-6 text-slate-600 font-medium">5.</span>
                  <span>Present students appear in the list</span>
                </div>
              </div>
            </div>
          )}
          
        </div>
      </div>
    </div>
  );
}
