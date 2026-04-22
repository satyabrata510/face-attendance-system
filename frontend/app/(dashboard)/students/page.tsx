"use client";

import { useState, useEffect, useRef } from "react";
import { Download, Plus, Search, Filter, Loader2, AlertCircle, UploadCloud, User, X, Trash2, Camera as CameraIcon } from "lucide-react";

export default function StudentsPage() {
  const [students, setStudents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState<any | null>(null);
  const [isPhotoExpanded, setIsPhotoExpanded] = useState(false);
  const [isDeleting, setIsDeleting] = useState<number | null>(null);
  
  // Add Student States
  const [isAddingStudent, setIsAddingStudent] = useState(false);
  const [newStudent, setNewStudent] = useState({ name: "", roll_no: "", department: "", dob: "" });
  const [newStudentPhoto, setNewStudentPhoto] = useState<Blob | null>(null);
  const [isFormSubmitting, setIsFormSubmitting] = useState(false);
  const addVideoRef = useRef<HTMLVideoElement>(null);
  const addCanvasRef = useRef<HTMLCanvasElement>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const addStreamRef = useRef<MediaStream | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);

  const deleteStudent = async (id: number) => {
    if (!confirm("Are you sure you want to delete this student? Face encodings and attendance records will also be removed.")) return;
    
    try {
      setIsDeleting(id);
      let token = localStorage.getItem("access_token");
      const res = await fetch(`http://localhost:8000/api/students/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      
      if (!res.ok) throw new Error("Failed to delete student.");
      await fetchStudents();
    } catch (err: any) {
      alert(err.message || "Failed to delete.");
    } finally {
      setIsDeleting(null);
    }
  };

  const fetchStudents = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const loginAndGetToken = async () => {
        const authRes = await fetch("http://localhost:8000/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams({ username: "Satya01", password: "Satya@123" }),
        });
        if (!authRes.ok) throw new Error("Failed to authenticate with backend.");
        const authData = await authRes.json();
        if (authData.access_token) {
          localStorage.setItem("access_token", authData.access_token);
        }
        return authData.access_token;
      };

      let token = localStorage.getItem("access_token");
      if (!token) {
        token = await loginAndGetToken();
      }

      // Fetch students via the API
      let res = await fetch("http://localhost:8000/api/students", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      
      // If unauthorized, token might be expired. Force a new login and retry.
      if (res.status === 401) {
        token = await loginAndGetToken();
        res = await fetch("http://localhost:8000/api/students", {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (!res.ok) throw new Error("Session completely expired. Please check credentials.");
      }
      
      if (!res.ok) throw new Error("Failed to fetch students data");
      const data = await res.json();
      
      if (data && data.students) {
        setStudents(data.students);
      } else {
        setStudents([]);
      }
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, []);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setIsUploading(true);
      setError(null);
      
      const formData = new FormData();
      formData.append("file", file);

      const token = localStorage.getItem("access_token");
      
      const res = await fetch("http://localhost:8000/api/students/import", {
        method: "POST",
        headers: { "Authorization": `Bearer \${token}` },
        body: formData
      });

      if (!res.ok) throw new Error("Failed to import students data.");

      const data = await res.json();
      alert(`Successfully imported records!`);
      
      await fetchStudents();
    } catch (err: any) {
      setError(err.message || "Failed to upload file.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const startAddCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      addStreamRef.current = stream;
      setIsCameraActive(true);
      setTimeout(() => {
        if (addVideoRef.current) {
          addVideoRef.current.srcObject = stream;
          addVideoRef.current.play().catch(console.error);
        }
      }, 100);
    } catch (err) {
      alert("Camera access denied.");
    }
  };

  const stopAddCamera = () => {
    if (addStreamRef.current) {
      addStreamRef.current.getTracks().forEach(track => track.stop());
      addStreamRef.current = null;
    }
    setIsCameraActive(false);
  };

  const capturePhoto = () => {
    if (!addVideoRef.current || !addCanvasRef.current) return;
    const video = addVideoRef.current;
    const canvas = addCanvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    
    // Draw mirrored video frame to canvas
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Reset transform just in case
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    
    canvas.toBlob((blob) => {
      if (blob) {
        setNewStudentPhoto(blob);
        setPhotoPreview(URL.createObjectURL(blob));
        stopAddCamera();
      }
    }, "image/jpeg", 0.9);
  };

  const cancelAddStudent = () => {
    setIsAddingStudent(false);
    setNewStudent({ name: "", roll_no: "", department: "", dob: "" });
    setNewStudentPhoto(null);
    setPhotoPreview(null);
    stopAddCamera();
  };

  const handleAddStudentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStudent.name || !newStudent.roll_no || !newStudent.department || !newStudentPhoto) {
      alert("Please fill all details and capture a facial photo to register biometrics.");
      return;
    }
    
    try {
      setIsFormSubmitting(true);
      const token = localStorage.getItem("access_token");
      
      // 1. Create student record
      const createRes = await fetch("http://localhost:8000/api/students", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(newStudent)
      });
      
      if (!createRes.ok) {
        const d = await createRes.json();
        throw new Error(d.detail || "Failed to create student.");
      }
      
      const createdStudent = await createRes.json();
      
      // 2. Upload face encoding
      const formData = new FormData();
      formData.append("file", newStudentPhoto, "face.jpg");
      
      const faceRes = await fetch(`http://localhost:8000/api/students/${createdStudent.id}/face`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData
      });
      
      if (!faceRes.ok) {
        const ef = await faceRes.json();
        throw new Error(ef.detail || "Student created but strict face recognition failed. Avoid dark or blurred photos!");
      }
      
      alert("Student added successfully!");
      cancelAddStudent();
      await fetchStudents();
    } catch (err: any) {
      alert(err.message || "Something went wrong.");
    } finally {
      setIsFormSubmitting(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700 ease-out">
      
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Student Records</h1>
          <p className="text-slate-400 mt-2">Manage student database, facial encodings and attendance records.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <input 
            type="file" 
            accept=".xlsx, .xls, .csv" 
            className="hidden" 
            ref={fileInputRef}
            onChange={handleFileUpload}
          />
          <button 
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="glass flex items-center gap-2 px-4 py-2.5 rounded-xl text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10 transition-colors border border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.15)]"
          >
            {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
            <span className="font-medium text-sm">{isUploading ? "Uploading..." : "Import XLS"}</span>
          </button>
          <button className="glass flex items-center gap-2 px-4 py-2.5 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800 transition-colors">
            <Download className="w-4 h-4" />
            <span className="font-medium text-sm">Export CSV</span>
          </button>
          <button 
            onClick={() => setIsAddingStudent(true)}
            className="bg-blue-600 hover:bg-blue-500 text-white flex items-center gap-2 px-4 py-2.5 rounded-xl shadow-[0_0_20px_rgba(59,130,246,0.3)] transition-all duration-300"
          >
            <Plus className="w-4 h-4" />
            <span className="font-medium text-sm">Add Student</span>
          </button>
        </div>
      </div>

      <div className="glass-card overflow-hidden border border-slate-700/60 shadow-xl shadow-blue-900/5">
        <div className="p-4 border-b border-slate-700/50 flex flex-col sm:flex-row gap-4 items-center justify-between bg-slate-800/20">
          <div className="relative w-full sm:max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search by name or reg no..." 
              className="w-full bg-slate-900/50 border border-slate-700/50 text-slate-200 placeholder:text-slate-500 rounded-lg py-2 pl-9 pr-4 text-sm outline-none focus:border-blue-500/50 focus:ring-2 ring-blue-500/20 transition-all"
            />
          </div>
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-700/30 text-slate-300 text-sm hover:bg-slate-700/50 transition-colors border border-slate-600/30">
            <Filter className="w-4 h-4" />
            Filter by Branch
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-400">
            <thead className="text-xs uppercase bg-slate-900/50 text-slate-400 border-b border-slate-700/50">
              <tr>
                <th scope="col" className="px-6 py-4 font-medium">Student Name</th>
                <th scope="col" className="px-6 py-4 font-medium">Reg No</th>
                <th scope="col" className="px-6 py-4 font-medium">Branch</th>
                <th scope="col" className="px-6 py-4 font-medium">Attendance %</th>
                <th scope="col" className="px-6 py-4 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-400">
                    <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-500" />
                    <p>Loading records...</p>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <AlertCircle className="w-8 h-8 mx-auto mb-4 text-red-500" />
                    <p className="text-red-400">{error}</p>
                  </td>
                </tr>
              ) : students.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-500">
                    No students found.
                  </td>
                </tr>
              ) : (
                students.map((student) => (
                  <tr key={student.id} className="border-b border-slate-700/30 hover:bg-slate-800/30 transition-colors">
                    <td className="px-6 py-4 font-medium text-slate-200">
                      <div className="flex items-center gap-3">
                        {student.face_image_url ? (
                          <img src={`http://localhost:8000${student.face_image_url}`} alt={student.name} className="w-8 h-8 rounded-full object-cover bg-slate-800" />
                        ) : (
                          <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center text-xs text-slate-500">
                            {student.name.charAt(0)}
                          </div>
                        )}
                        {student.name}
                      </div>
                    </td>
                    <td className="px-6 py-4">{student.roll_no || "N/A"}</td>
                    <td className="px-6 py-4">
                      <span className="px-2.5 py-1 bg-slate-800 border border-slate-700 rounded-md text-xs font-medium text-slate-300">
                        {student.department || "N/A"}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span>{student.status || "Active"}</span>
                        <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${
                              student.status === 'Active' ? 'bg-emerald-500' : 'bg-red-500'
                            }`}
                            style={{ width: '100%' }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button 
                          onClick={() => setSelectedStudent(student)}
                          className="text-blue-400 hover:text-blue-300 font-medium px-3 py-1 rounded-md hover:bg-blue-500/10 transition-colors"
                        >
                          View Info
                        </button>
                        <button 
                          onClick={() => deleteStudent(student.id)}
                          disabled={isDeleting === student.id}
                          className="text-red-400 hover:text-red-300 p-2 rounded-md hover:bg-red-500/10 transition-colors disabled:opacity-50"
                          title="Delete Student"
                        >
                          {isDeleting === student.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Student Details Modal */}
      {selectedStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-[#0B1121] border border-slate-700/80 rounded-2xl p-6 w-full max-w-sm shadow-2xl relative">
            <button 
              onClick={() => setSelectedStudent(null)}
              className="absolute top-4 right-4 text-slate-500 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
            
            <div className="flex flex-col items-center text-center mt-2">
              <div 
                className="w-24 h-24 rounded-full bg-slate-800 border-[3px] border-[#10B981] overflow-hidden mb-4 flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.3)] cursor-pointer hover:border-white transition-all transform hover:scale-105"
                onClick={() => setIsPhotoExpanded(true)}
              >
                {(selectedStudent.face_image_url || selectedStudent.photo_url) ? (
                  <img 
                    src={`http://localhost:8000${selectedStudent.face_image_url || selectedStudent.photo_url}`} 
                    alt={selectedStudent.name} 
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <User className="w-10 h-10 text-slate-500" />
                )}
              </div>
              
              <h3 className="text-xl font-bold text-white tracking-tight">{selectedStudent.name}</h3>
              <p className="text-slate-400 text-sm font-medium mt-1 mb-6 uppercase tracking-wider">{selectedStudent.roll_no}</p>
              
              <div className="w-full grid grid-cols-2 gap-3 text-left">
                <div className="bg-slate-900/50 p-3.5 rounded-xl border border-slate-700/50">
                  <p className="text-[11px] font-semibold text-slate-400 mb-1 uppercase tracking-wider">Department</p>
                  <p className="font-medium text-slate-200 text-sm">{selectedStudent.department}</p>
                </div>
                <div className="bg-slate-900/50 p-3.5 rounded-xl border border-slate-700/50">
                  <p className="text-[11px] font-semibold text-slate-400 mb-1 uppercase tracking-wider">Date of Birth</p>
                  <p className="font-medium text-slate-200 text-sm">{selectedStudent.dob || "N/A"}</p>
                </div>
                <div className="bg-slate-900/50 p-3.5 rounded-xl border border-slate-700/50">
                  <p className="text-[11px] font-semibold text-slate-400 mb-1 uppercase tracking-wider">Status</p>
                  <p className="font-medium text-[#10B981] text-sm">{selectedStudent.status}</p>
                </div>
                <div className="bg-slate-900/50 p-3.5 rounded-xl border border-slate-700/50 col-span-2">
                  <p className="text-[11px] font-semibold text-slate-400 mb-2 uppercase tracking-wider">System Face Profile</p>
                  <div className="flex items-center gap-2.5">
                    <div className={`w-2 h-2 rounded-full shadow-[0_0_8px_currentColor] ${selectedStudent.has_face_registered ? "bg-[#10B981] text-[#10B981]" : "bg-amber-400 text-amber-400"}`}></div>
                    <p className="font-medium text-slate-200 text-sm">
                      {selectedStudent.has_face_registered ? "Biometrics Enrolled" : "Missing Direct Photo Encoding"}
                    </p>
                  </div>
                </div>
              </div>
              
              <button 
                onClick={() => setSelectedStudent(null)}
                className="w-full mt-6 bg-slate-800 hover:bg-slate-700 text-white py-2.5 rounded-xl text-sm font-semibold transition-colors"
              >
                Close Profile
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Full Screen Photo Overlay */}
      {isPhotoExpanded && selectedStudent && (selectedStudent.face_image_url || selectedStudent.photo_url) && (
        <div 
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/95 animate-in fade-in zoom-in-95 duration-200 p-4"
          onClick={() => setIsPhotoExpanded(false)}
        >
          <button 
            onClick={(e) => { e.stopPropagation(); setIsPhotoExpanded(false); }}
            className="absolute top-6 right-6 text-white/70 hover:text-white transition-colors bg-white/10 hover:bg-white/20 p-2 rounded-full"
          >
            <X className="w-6 h-6" />
          </button>
          <img 
            src={`http://localhost:8000${selectedStudent.face_image_url || selectedStudent.photo_url}`} 
            alt={selectedStudent.name} 
            className="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {/* Add Student Modal */}
      {isAddingStudent && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-[#0B1121] border border-slate-700/80 rounded-2xl w-full max-w-2xl shadow-2xl relative flex flex-col max-h-[90vh]">
            <div className="p-6 border-b border-slate-800 flex justify-between items-center">
              <h2 className="text-xl font-bold text-white">Add New Student</h2>
              <button disabled={isFormSubmitting} onClick={cancelAddStudent} className="text-slate-500 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto custom-scrollbar">
              <form id="add-student-form" onSubmit={handleAddStudentSubmit} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div className="space-y-2">
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Full Name</label>
                    <input required type="text" value={newStudent.name} onChange={(e) => setNewStudent({...newStudent, name: e.target.value})} className="w-full bg-slate-900/50 border border-slate-700/50 text-slate-200 rounded-lg p-3 text-sm outline-none focus:border-blue-500/50 focus:ring-1 ring-blue-500/50" placeholder="e.g. John Doe" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Reg No</label>
                    <input required type="text" value={newStudent.roll_no} onChange={(e) => setNewStudent({...newStudent, roll_no: e.target.value})} className="w-full bg-slate-900/50 border border-slate-700/50 text-slate-200 rounded-lg p-3 text-sm outline-none focus:border-blue-500/50 focus:ring-1 ring-blue-500/50" placeholder="e.g. 2301010101" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Branch</label>
                    <input required type="text" value={newStudent.department} onChange={(e) => setNewStudent({...newStudent, department: e.target.value})} className="w-full bg-slate-900/50 border border-slate-700/50 text-slate-200 rounded-lg p-3 text-sm outline-none focus:border-blue-500/50 focus:ring-1 ring-blue-500/50" placeholder="e.g. CSE" />
                  </div>
                  <div className="space-y-2">
                    <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Date of Birth</label>
                    <input required type="date" value={newStudent.dob} onChange={(e) => setNewStudent({...newStudent, dob: e.target.value})} className="w-full bg-slate-900/50 border border-slate-700/50 text-slate-400 rounded-lg p-3 text-sm outline-none focus:border-blue-500/50 focus:ring-1 ring-blue-500/50 [color-scheme:dark]" />
                  </div>
                </div>

                <div className="border border-slate-700/50 rounded-xl p-5 bg-slate-900/30">
                  <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-4">Student Face Registration Preview</label>
                  
                  <div className="flex flex-col items-center">
                    {photoPreview ? (
                      <div className="relative mb-2">
                        <img src={photoPreview} alt="Preview" className="w-32 h-32 rounded-full object-cover border-[3px] border-[#10B981]" />
                        <button type="button" onClick={() => { setPhotoPreview(null); setNewStudentPhoto(null); }} className="absolute -top-2 -right-2 bg-slate-800 text-red-400 rounded-full p-1 border border-slate-600 hover:text-red-300">
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : isCameraActive ? (
                      <div className="flex flex-col items-center w-full mb-2">
                        <div className="w-full max-w-[280px] aspect-square bg-[#020617] rounded-xl overflow-hidden relative mb-4 border border-blue-500/30">
                          <video ref={addVideoRef} className="absolute inset-0 w-full h-full object-cover scale-x-[-1]" playsInline muted />
                          <canvas ref={addCanvasRef} className="hidden" />
                          <div className="absolute inset-0 pointer-events-none border-[1.5px] border-emerald-500/40 m-4 rounded-lg" style={{ borderStyle: 'dashed' }}></div>
                        </div>
                        <div className="flex gap-3">
                          <button type="button" onClick={capturePhoto} className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-semibold transition-colors shadow-lg shadow-emerald-900/20">Capture Face</button>
                          <button type="button" onClick={stopAddCamera} className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-semibold transition-colors">Cancel</button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex gap-4">
                        <button type="button" onClick={startAddCamera} className="flex flex-col items-center justify-center gap-2 w-32 h-32 rounded-2xl border-2 border-dashed border-slate-600/60 hover:border-blue-500/50 bg-slate-800/20 hover:bg-slate-800/50 text-slate-400 hover:text-blue-400 transition-colors">
                          <CameraIcon className="w-8 h-8 opacity-80" />
                          <span className="text-[11px] font-semibold tracking-wide">Live Snapshot</span>
                        </button>

                        <button 
                          type="button" 
                          onClick={() => document.getElementById('student-photo-upload')?.click()}
                          className="flex flex-col items-center justify-center gap-2 w-32 h-32 rounded-2xl border-2 border-dashed border-slate-600/60 hover:border-emerald-500/50 bg-slate-800/20 hover:bg-slate-800/50 text-slate-400 hover:text-emerald-400 transition-colors"
                        >
                          <UploadCloud className="w-8 h-8 opacity-80" />
                          <span className="text-[11px] font-semibold tracking-wide">Upload Photo</span>
                        </button>
                        <input 
                          type="file" 
                          id="student-photo-upload" 
                          className="hidden" 
                          accept="image/*" 
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) {
                              setNewStudentPhoto(file);
                              setPhotoPreview(URL.createObjectURL(file));
                            }
                          }} 
                        />
                      </div>
                    )}
                  </div>
                </div>
              </form>
            </div>
            
            <div className="p-6 border-t border-slate-800 flex justify-end gap-3 mt-auto">
              <button disabled={isFormSubmitting} onClick={cancelAddStudent} type="button" className="px-5 py-2.5 text-slate-400 hover:text-white font-medium text-sm transition-colors">Cancel</button>
              <button form="add-student-form" type="submit" disabled={isFormSubmitting} className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50 text-white rounded-xl font-semibold shadow-[0_0_15px_rgba(59,130,246,0.3)] transition-colors flex items-center gap-2 text-sm">
                {isFormSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                {isFormSubmitting ? "Registering..." : "Save Student"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
