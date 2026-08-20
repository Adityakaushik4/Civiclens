import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listRagDocuments, ingestRagDocument } from '../../api/rag';
import { BookOpen, Upload, FileText, CheckCircle2, AlertCircle, Database, Search, RotateCw } from 'lucide-react';

export const AdminRagPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  const { data: ragDocs = [], isLoading } = useQuery({
    queryKey: ['adminRagDocs'],
    queryFn: listRagDocuments,
  });

  const ingestMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('title', file.name.replace(/\.[^/.]+$/, ''));
      formData.append('issuing_authority', 'Municipal Admin');
      formData.append('document_type', 'POLICY');
      formData.append('authority_status', 'PROVISIONAL');
      formData.append('access_level', 'PUBLIC');
      formData.append('file', file);
      return ingestRagDocument(formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adminRagDocs'] });
      setIsUploading(false);
    },
    onError: () => {
      setIsUploading(false);
    },
  });

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setIsUploading(true);
      ingestMutation.mutate(e.target.files[0]);
    }
  };

  const filteredDocs = ragDocs.filter(doc => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      doc.title.toLowerCase().includes(term) ||
      doc.issuing_authority.toLowerCase().includes(term) ||
      doc.document_type.toLowerCase().includes(term)
    );
  });

  const totalDocs = ragDocs.length;
  const indexedDocs = ragDocs.filter(d => (d.authority_status || '').toUpperCase() !== 'FAILED').length;
  const failedDocs = ragDocs.filter(d => (d.authority_status || '').toUpperCase() === 'FAILED').length;

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <Database className="w-6 h-6 text-blue-600" /> Knowledge Base (RAG)
          </h1>
          <p className="text-xs text-slate-600">Manage statutory documents, SOPs, and policies for the AI reasoning engine.</p>
        </div>

        <label className="px-5 py-2.5 rounded-xl bg-blue-700 hover:bg-blue-800 text-white font-semibold text-xs flex items-center gap-2 shadow-sm transition-all cursor-pointer">
          <Upload className="w-4 h-4" /> {isUploading ? 'Ingesting Document...' : 'Ingest Document'}
          <input type="file" onChange={handleFileUpload} disabled={isUploading} className="hidden" accept=".pdf,.docx,.txt" />
        </label>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white/80 border border-slate-200 rounded-lg p-4">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
              <FileText className="w-5 h-5 text-blue-400" />
            </div>
            <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Total Docs</h3>
          </div>
          <div className="text-2xl font-bold text-slate-900">{isLoading ? '...' : totalDocs}</div>
        </div>

        <div className="bg-white/80 border border-slate-200 rounded-lg p-4">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Indexed</h3>
          </div>
          <div className="text-2xl font-bold text-slate-900">{isLoading ? '...' : indexedDocs}</div>
        </div>

        <div className="bg-white/80 border border-slate-200 rounded-lg p-4">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
              <RotateCw className="w-5 h-5 text-amber-400" />
            </div>
            <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Pending</h3>
          </div>
          <div className="text-2xl font-bold text-slate-900">0</div>
        </div>

        <div className="bg-white/80 border border-slate-200 rounded-lg p-4">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-2 bg-rose-500/10 rounded-lg border border-rose-500/20">
              <AlertCircle className="w-5 h-5 text-rose-400" />
            </div>
            <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Failed</h3>
          </div>
          <div className="text-2xl font-bold text-slate-900">{isLoading ? '...' : failedDocs}</div>
        </div>
      </div>

      {/* Upload area */}
      <label className="border-2 border-dashed border-slate-300 bg-white/30 rounded-xl p-8 flex flex-col items-center justify-center text-center space-y-3 hover:bg-white/50 transition-colors cursor-pointer block">
        <div className="p-3 bg-slate-50 rounded-full">
          <Upload className="w-6 h-6 text-slate-700" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-slate-900">Drag & drop municipal documents here</h3>
          <p className="text-xs text-slate-600 mt-1">Supports PDF, DOCX, and TXT (Max 50MB). Documents will be chunked and indexed automatically.</p>
        </div>
        <input type="file" onChange={handleFileUpload} disabled={isUploading} className="hidden" accept=".pdf,.docx,.txt" />
      </label>

      {/* Document List */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-bold text-slate-900">Indexed Documents</h3>
          <div className="relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 transform -translate-y-1/2" />
            <input 
              type="text" 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search knowledge base..." 
              className="bg-white border border-slate-200 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-900 w-64 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        <div className="bg-white/80 border border-slate-200 rounded-xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-white text-slate-600 font-semibold border-b border-slate-200">
              <tr>
                <th className="p-4">Document ID / Title</th>
                <th className="p-4">Type</th>
                <th className="p-4">Issuing Authority</th>
                <th className="p-4">Version</th>
                <th className="p-4">Status</th>
                <th className="p-4 flex justify-end">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-500">
                    Loading knowledge-base documents...
                  </td>
                </tr>
              ) : filteredDocs && filteredDocs.length > 0 ? (
                filteredDocs.map((doc, idx) => (
                  <tr key={doc.document_id || doc.doc_id || idx} className="hover:bg-slate-50/40">
                    <td className="p-4 font-semibold text-slate-900 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-blue-600" />
                      <div>
                        <div>{doc.title}</div>
                        <div className="text-[10px] font-mono text-slate-500">{doc.document_id || doc.doc_id}</div>
                        {doc.source_reference && (
                          <div className="text-[10px] text-blue-600 mt-0.5 truncate max-w-xs" title={doc.source_reference}>
                            {doc.authority_status === 'AUTHORITATIVE' && <span className="font-bold mr-1">Official Source:</span>}
                            <a href={doc.source_reference} target="_blank" rel="noopener noreferrer" className="hover:underline">
                              {doc.source_reference}
                            </a>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="p-4">
                      <span className="text-[10px] font-bold text-slate-700 bg-slate-50 px-2 py-0.5 rounded-md">
                        {doc.document_type}
                      </span>
                    </td>
                    <td className="p-4">{doc.issuing_authority || 'Municipal Admin'}</td>
                    <td className="p-4 text-slate-600 font-mono text-[10px]">{doc.current_version_id || 'v1.0'}</td>
                    <td className="p-4">
                      {doc.authority_status === 'AUTHORITATIVE' ? (
                        <span className="bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full font-bold flex items-center gap-1 w-fit whitespace-nowrap">
                          <CheckCircle2 className="w-3 h-3" /> OFFICIAL GOVERNMENT SOURCE
                        </span>
                      ) : doc.authority_status === 'PROVISIONAL' ? (
                        <span className="bg-slate-50 text-slate-600 border border-slate-200 px-2 py-0.5 rounded-full font-bold flex items-center gap-1 w-fit whitespace-nowrap">
                          <AlertCircle className="w-3 h-3" /> USER-UPLOADED DOCUMENT
                        </span>
                      ) : (
                        <span className="bg-slate-500/10 text-slate-600 border border-slate-500/20 px-2 py-0.5 rounded-full font-bold flex items-center gap-1 w-fit whitespace-nowrap">
                          <RotateCw className="w-3 h-3" /> INTERNAL / SYSTEM DOCUMENT
                        </span>
                      )}
                    </td>
                    <td className="p-4 flex items-center justify-end gap-2">
                      <button className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-50 rounded-lg transition-colors" title="View Document">
                        <BookOpen className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-slate-500">
                    No knowledge-base documents indexed yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
