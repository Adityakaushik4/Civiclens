import React from 'react';
import { Shield, Sparkles, Lock } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white border-t border-slate-900 text-slate-600 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          <div className="md:col-span-2">
            <div className="flex items-center space-x-2 mb-3">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
                <Shield className="w-5 h-5 text-slate-900" />
              </div>
              <span className="font-bold text-lg text-slate-900">CivicLens AI</span>
            </div>
            <p className="text-sm text-slate-600 max-w-sm mb-4 leading-relaxed">
              Unified Multilingual Civic Intelligence & Participatory Governance Platform for Smart Cities.
            </p>
            <div className="flex items-center space-x-4 text-xs text-slate-500">
              <span className="flex items-center gap-1 text-emerald-400">
                <Lock className="w-3.5 h-3.5" /> Privacy-Preserving Fuzzing
              </span>
              <span className="flex items-center gap-1 text-blue-400">
                <Sparkles className="w-3.5 h-3.5" /> Multilingual Gemini 3.6 AI
              </span>
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-slate-900 text-sm mb-3">Public Portals</h4>
            <ul className="space-y-2 text-sm">
              <li><a href="/public" className="hover:text-blue-400 transition-colors">Civic Transparency</a></li>
              <li><a href="/public/hotspots" className="hover:text-blue-400 transition-colors">Hotspot Projects</a></li>
              <li><a href="/public/budget" className="hover:text-blue-400 transition-colors">Participatory Budget</a></li>
              <li><a href="/citizen/report" className="hover:text-blue-400 transition-colors">Report an Issue</a></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-slate-900 text-sm mb-3">Governance Engine</h4>
            <ul className="space-y-2 text-sm text-slate-600">
              <li>Phase 1: Multilingual AI</li>
              <li>Phase 2: STT & Vision Fusion</li>
              <li>Phase 3: Duplicate Engine</li>
              <li>Phase 4: SLA & Priority Routing</li>
              <li>Phase 5: Evidence & Verification</li>
              <li>Phase 6: Grounded RAG Knowledge</li>
              <li>Phase 7: Participatory Budgeting</li>
            </ul>
          </div>
        </div>

        <div className="border-t border-slate-900 pt-6 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500">
          <p>© 2026 CivicLens. Built for SIH Municipal Innovation.</p>
        </div>
      </div>
    </footer>
  );
};
