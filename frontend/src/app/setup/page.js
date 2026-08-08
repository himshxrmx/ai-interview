"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { uploadCandidateData } from "@/lib/api";

export default function SetupPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Form State
  const [curriculumFile, setCurriculumFile] = useState(null);
  const [curriculumText, setCurriculumText] = useState("");

  const [profileFile, setProfileFile] = useState(null);
  const [profileText, setProfileText] = useState("");

  const [specFile, setSpecFile] = useState(null);
  const [specText, setSpecText] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      if (curriculumFile) formData.append("curriculum_file", curriculumFile);
      if (curriculumText) formData.append("curriculum_text", curriculumText);
      if (profileFile) formData.append("profile_file", profileFile);
      if (profileText) formData.append("profile_text", profileText);
      if (specFile) formData.append("specialization_file", specFile);
      if (specText) formData.append("specialization_text", specText);

      const { candidate_id } = await uploadCandidateData(formData);
      router.push(`/?candidate_id=${candidate_id}`);
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050810] text-slate-200 font-sans flex flex-col items-center justify-center py-16 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      
      {/* Background Orbs */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-cyan-600/15 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-indigo-600/15 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-3xl w-full space-y-10 relative z-10">
        
        {/* Header */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center p-3 mb-2 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-cyan-500/20 border border-indigo-500/20 shadow-[0_0_30px_rgba(99,102,241,0.2)]">
            <svg className="w-8 h-8 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path>
            </svg>
          </div>
          <h2 className="text-4xl sm:text-5xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-indigo-400 to-purple-400">
            Interview Context
          </h2>
          <p className="text-slate-400 text-sm sm:text-base font-medium max-w-xl mx-auto">
            Upload the candidate's documentation to generate a deeply personalized and dynamic technical assessment.
          </p>
        </div>

        <form className="mt-8 bg-[#0a0e17]/80 backdrop-blur-xl p-8 sm:p-10 rounded-3xl border border-white/5 shadow-2xl space-y-8" onSubmit={handleSubmit}>
          
          {error && (
            <div className="flex items-center gap-3 rounded-xl bg-red-500/10 p-4 border border-red-500/20">
              <svg className="w-5 h-5 text-red-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm font-medium text-red-200">{error}</p>
            </div>
          )}

          <div className="space-y-8">
            {/* Field 1: Curriculum */}
            <div className="group">
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3 uppercase tracking-wider">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-400 text-xs">1</span>
                Curriculum / Syllabus
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="relative flex flex-col items-center justify-center p-6 border-2 border-dashed border-slate-700/50 rounded-2xl bg-slate-900/30 hover:bg-slate-800/50 hover:border-cyan-500/50 transition-all cursor-pointer overflow-hidden group-hover:shadow-[0_0_20px_rgba(34,211,238,0.05)]">
                  <input
                    type="file"
                    accept=".pdf,.txt"
                    onChange={(e) => setCurriculumFile(e.target.files[0])}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <div className="flex flex-col items-center gap-2 text-slate-400">
                    <svg className="w-8 h-8 text-cyan-500/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span className="text-sm font-medium">{curriculumFile ? curriculumFile.name : "Upload PDF/TXT"}</span>
                  </div>
                </div>
                <textarea
                  placeholder="Or paste text..."
                  value={curriculumText}
                  onChange={(e) => setCurriculumText(e.target.value)}
                  className="w-full resize-none rounded-2xl bg-slate-900/50 border border-slate-700/50 text-slate-200 p-4 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 placeholder:text-slate-600 transition-all h-full min-h-[120px]"
                />
              </div>
            </div>

            {/* Field 2: Profile */}
            <div className="group">
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3 uppercase tracking-wider">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 text-xs">2</span>
                Candidate Profile
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="relative flex flex-col items-center justify-center p-6 border-2 border-dashed border-slate-700/50 rounded-2xl bg-slate-900/30 hover:bg-slate-800/50 hover:border-indigo-500/50 transition-all cursor-pointer overflow-hidden group-hover:shadow-[0_0_20px_rgba(99,102,241,0.05)]">
                  <input
                    type="file"
                    accept=".pdf,.txt"
                    onChange={(e) => setProfileFile(e.target.files[0])}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <div className="flex flex-col items-center gap-2 text-slate-400">
                    <svg className="w-8 h-8 text-indigo-500/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    <span className="text-sm font-medium">{profileFile ? profileFile.name : "Upload Resume"}</span>
                  </div>
                </div>
                <textarea
                  placeholder="Or paste resume..."
                  value={profileText}
                  onChange={(e) => setProfileText(e.target.value)}
                  className="w-full resize-none rounded-2xl bg-slate-900/50 border border-slate-700/50 text-slate-200 p-4 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500/50 placeholder:text-slate-600 transition-all h-full min-h-[120px]"
                />
              </div>
            </div>

            {/* Field 3: Specialization */}
            <div className="group">
              <label className="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-3 uppercase tracking-wider">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-purple-500/20 text-purple-400 text-xs">3</span>
                Technical Context
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="relative flex flex-col items-center justify-center p-6 border-2 border-dashed border-slate-700/50 rounded-2xl bg-slate-900/30 hover:bg-slate-800/50 hover:border-purple-500/50 transition-all cursor-pointer overflow-hidden group-hover:shadow-[0_0_20px_rgba(168,85,247,0.05)]">
                  <input
                    type="file"
                    accept=".pdf,.txt"
                    onChange={(e) => setSpecFile(e.target.files[0])}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <div className="flex flex-col items-center gap-2 text-slate-400">
                    <svg className="w-8 h-8 text-purple-500/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                    </svg>
                    <span className="text-sm font-medium">{specFile ? specFile.name : "Upload Projects"}</span>
                  </div>
                </div>
                <textarea
                  placeholder="Or paste context..."
                  value={specText}
                  onChange={(e) => setSpecText(e.target.value)}
                  className="w-full resize-none rounded-2xl bg-slate-900/50 border border-slate-700/50 text-slate-200 p-4 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 placeholder:text-slate-600 transition-all h-full min-h-[120px]"
                />
              </div>
            </div>
          </div>

          <div className="pt-4">
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center items-center gap-2 py-4 px-6 border border-transparent text-base font-bold rounded-2xl text-white bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#0a0e17] focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-[0_0_30px_rgba(99,102,241,0.2)] hover:shadow-[0_0_40px_rgba(34,211,238,0.4)] overflow-hidden"
            >
              <div className="absolute inset-0 bg-white/20 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 ease-in-out" />
              {isLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Processing Context...
                </>
              ) : (
                <>
                  Launch Agentic Interview
                  <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
