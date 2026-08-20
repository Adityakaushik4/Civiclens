import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getPublicIssueView, getPublicIssueTimeline, reopenIssue } from '../../api/issues';
import { getIssueEvidence } from '../../api/evidence';
import { explainRouting, explainSLA } from '../../api/rag';
import {
  CheckCircle2,
  Clock,
  AlertTriangle,
  Building,
  ArrowLeft,
  RotateCcw,
  Sparkles,
  HelpCircle,
  FileCheck,
  ImageIcon,
  Volume2,
  FileText,
} from 'lucide-react';

const EvidenceImagePreview: React.FC<{ mediaUrl: string; fileName: string }> = ({ mediaUrl, fileName }) => {
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return (
      <div className="bg-slate-50 border border-slate-200 rounded-lg h-44 flex flex-col items-center justify-center gap-1.5 text-slate-500 p-4">
        <ImageIcon className="w-6 h-6 text-slate-400" />
        <span className="text-xs font-medium text-slate-600">Preview unavailable</span>
      </div>
    );
  }

  return (
    <div className="rounded-lg overflow-hidden h-44 sm:h-48 border border-slate-200 bg-slate-950/5 relative group">
      <img
        src={mediaUrl}
        alt={fileName}
        onError={() => setHasError(true)}
        className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
      />
    </div>
  );
};

export const CitizenIssueDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [reopenReason, setReopenReason] = useState('');
  const [showReopenModal, setShowReopenModal] = useState(false);
  const [showRagExplain, setShowRagExplain] = useState<'routing' | 'sla' | null>(null);

  const rawId = id || 'CIVIC-2026-C537';

  // 1. Fetch public view (accepts either public_id or internal issue_id)
  const { data: issue, isLoading: isIssueLoading, isError: isIssueError } = useQuery({
    queryKey: ['publicIssue', rawId],
    queryFn: () => getPublicIssueView(rawId),
  });

  const publicId = issue?.public_id || rawId;
  const internalId = issue?.issue_id || rawId;

  // 2. Fetch public timeline using public tracking ID
  const { data: timeline } = useQuery({
    queryKey: ['publicTimeline', publicId],
    queryFn: () => getPublicIssueTimeline(publicId),
  });

  // 3. Fetch evidence logs using internal issue UUID
  const { data: evidenceData } = useQuery({
    queryKey: ['issueEvidence', internalId],
    queryFn: () => getIssueEvidence(internalId),
  });

  // 4. Fetch grounded RAG explanation using internal issue UUID
  const { data: ragExplanation } = useQuery({
    queryKey: ['ragExplain', showRagExplain, internalId],
    queryFn: () => (showRagExplain === 'routing' ? explainRouting(internalId) : explainSLA(internalId)),
    enabled: !!showRagExplain,
  });

  // 5. Reopen mutation using internal issue UUID
  const reopenMutation = useMutation({
    mutationFn: (reason: string) => reopenIssue(internalId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['publicIssue', rawId] });
      queryClient.invalidateQueries({ queryKey: ['publicTimeline', publicId] });
      setShowReopenModal(false);
    },
  });

  const timelineSteps = [
    'REPORTED',
    'ROUTED',
    'ACKNOWLEDGED',
    'IN_PROGRESS',
    'AWAITING_VERIFICATION',
    'RESOLVED',
  ];

  const rawStatus = issue?.status?.toUpperCase() || 'REGISTERED';
  const mappedStatus = (rawStatus === 'PENDING ROUTING' || rawStatus === 'REGISTERED') ? 'REPORTED' : rawStatus;
  const currentStatusIndex = timelineSteps.indexOf(mappedStatus);

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      <Link to="/citizen/issues" className="inline-flex items-center text-xs text-slate-600 hover:text-slate-900 gap-1 font-semibold">
        <ArrowLeft className="w-4 h-4" /> Back to My Issues
      </Link>

      {isIssueLoading && (
        <div className="bg-white/80 border border-slate-200 rounded-xl p-12 text-center text-slate-600">
          Loading issue details...
        </div>
      )}

      {isIssueError && (
        <div className="bg-white/80 border border-slate-200 rounded-xl p-12 text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto" />
          <h3 className="text-lg font-bold text-slate-900">Details currently unavailable / still processing</h3>
          <p className="text-xs text-slate-600 max-w-sm mx-auto">
            The issue <span className="font-mono text-slate-900">{rawId}</span> exists, but detailed public tracking and timeline information are not yet available. It may be pending initial review and routing.
          </p>
        </div>
      )}

      {issue && (
        <>
      {/* Header Card */}
      <div className="bg-white/80 border border-slate-200 rounded-xl p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-mono text-xs text-blue-700 font-bold bg-blue-50 px-2.5 py-1 rounded-full border border-blue-200">
                {issue.public_id}
              </span>
              <span className="bg-slate-50 text-slate-700 text-xs px-2.5 py-1 rounded-full font-medium">
                {issue.category} / {issue.subcategory}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-2">
              {issue.category.replace('_', ' ')} Issue near {issue.public_location_description}
            </h1>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => setShowRagExplain(showRagExplain === 'routing' ? null : 'routing')}
              className="px-3.5 py-2 rounded-xl bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-100 text-xs font-semibold flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5" /> Explain Routing
            </button>
            <button
              onClick={() => setShowRagExplain(showRagExplain === 'sla' ? null : 'sla')}
              className="px-3.5 py-2 rounded-xl bg-slate-50 border border-slate-200 text-slate-700 hover:bg-slate-100 text-xs font-semibold flex items-center gap-1.5"
            >
              <HelpCircle className="w-3.5 h-3.5" /> Explain SLA
            </button>
          </div>
        </div>

        {/* RAG Explanation Modal / Box */}
        {showRagExplain && ragExplanation && (
          <div className="bg-white border border-blue-200 rounded-lg p-5 space-y-3 shadow-sm">
            <div className="flex items-center justify-between text-xs text-blue-700 font-bold uppercase tracking-wider">
              <span className="flex items-center gap-1">
                <Sparkles className="w-4 h-4" /> Grounded RAG Explanation ({showRagExplain.toUpperCase()})
              </span>
              <button onClick={() => setShowRagExplain(null)} className="text-slate-600 hover:text-slate-900">✕</button>
            </div>
            <p className="text-xs text-slate-800 leading-relaxed font-medium">{ragExplanation.answer}</p>
            {ragExplanation.citations && ragExplanation.citations.length > 0 && (
              <div className="pt-2 border-t border-slate-200 text-[11px] text-slate-600 space-y-1">
                <span className="font-semibold text-slate-700">Statutory Citation Reference:</span>
                {ragExplanation.citations.map((c, i) => (
                  <p key={i} className="font-mono text-blue-700">
                    • {c.document_title} ({c.issuing_authority}) — {c.section}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-200/80 text-xs">
          <div>
            <span className="text-slate-500 block">Department</span>
            <span className="font-bold text-slate-900 flex items-center gap-1 mt-0.5">
              <Building className="w-3.5 h-3.5 text-blue-600" /> {issue.department_name}
            </span>
          </div>

          <div>
            <span className="text-slate-500 block">Priority Tier</span>
            <span className="font-bold text-amber-600 flex items-center gap-1 mt-0.5">
              <AlertTriangle className="w-3.5 h-3.5" /> {issue.priority_level}
            </span>
          </div>

          <div>
            <span className="text-slate-500 block">SLA Timer</span>
            {issue.status === 'Pending Routing' ? (
              <span className="font-bold text-slate-600 flex items-center gap-1 mt-0.5">
                Not available
              </span>
            ) : (
              <span className="font-bold text-emerald-600 flex items-center gap-1 mt-0.5">
                <Clock className="w-3.5 h-3.5" /> Active
              </span>
            )}
          </div>

          <div>
            <span className="text-slate-500 block">Resolution Status</span>
            <span className="font-bold text-blue-600 mt-0.5 block">
              {issue.status}
            </span>
          </div>
        </div>
      </div>

      {/* Visual Timeline (Section 3.D) */}
      <div className="bg-white/80 border border-slate-200 rounded-xl p-6 sm:p-8 space-y-6">
        <h3 className="text-lg font-bold text-slate-900">Visual Resolution Lifecycle</h3>

        <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
          {timelineSteps.map((stepName, idx) => {
            const isCompleted = idx <= currentStatusIndex;
            const isCurrent = idx === currentStatusIndex;

            return (
              <div
                key={stepName}
                className={`p-3 rounded-lg border text-center space-y-2 transition-all ${
                  isCurrent
                    ? 'bg-blue-50 border-blue-300 text-blue-700 shadow-sm'
                    : isCompleted
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                    : 'bg-slate-50 border-slate-200 text-slate-600'
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-full mx-auto flex items-center justify-center font-bold text-xs ${
                    isCurrent
                      ? 'bg-blue-600 text-white shadow-sm'
                      : isCompleted
                      ? 'bg-emerald-500 text-white shadow-sm'
                      : 'bg-slate-200 text-slate-500'
                  }`}
                >
                  {idx + 1}
                </div>
                <span className="text-[11px] font-bold block tracking-wider uppercase">{stepName}</span>
              </div>
            );
          })}
        </div>

        {/* Timeline Entries List */}
        <div className="space-y-3 pt-4 border-t border-slate-200/80">
          <h4 className="text-sm font-bold text-slate-900">Activity Log</h4>
          {timeline && timeline.length > 0 ? (
            timeline.map((entry, i) => (
              <div key={i} className="flex items-start space-x-3 text-xs bg-slate-50 p-3 rounded-xl border border-slate-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <span className="font-semibold text-slate-900">{entry.event}</span>
                  {entry.public_note && <p className="text-slate-600">{entry.public_note}</p>}
                  <span className="text-[10px] text-slate-500 block font-mono">{entry.timestamp}</span>
                </div>
              </div>
            ))
          ) : (
            <div className="text-xs text-slate-600 p-3 bg-white/40 rounded-xl border border-slate-200">
              Activity timeline is not yet available for this issue. It is pending initial assessment.
            </div>
          )}
        </div>
      </div>

      {/* Resolution Evidence Display */}
      {evidenceData && evidenceData.evidence && evidenceData.evidence.length > 0 && (
        <div className="bg-white/80 border border-slate-200 rounded-xl p-6 sm:p-8 space-y-4">
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <FileCheck className="w-5 h-5 text-emerald-600" /> Resolution Evidence Records
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {evidenceData.evidence.map((ev) => {
              const mediaUrl =
                ev.media_url ||
                (ev.public_token ? `/api/v1/public/evidence/${ev.issue_id || internalId}/media/${ev.public_token}` : null);
              const isAudio =
                (ev.mime_type || '').startsWith('audio/') ||
                ev.evidence_type === 'VOICE_NOTE' ||
                ev.file_name.endsWith('.wav') ||
                ev.file_name.endsWith('.mp3');
              const isImage =
                (ev.mime_type || '').startsWith('image/') ||
                ev.evidence_type === 'BEFORE_IMAGE' ||
                ev.evidence_type === 'AFTER_IMAGE' ||
                /\.(jpg|jpeg|png|webp)$/i.test(ev.file_name);

              const getEvidenceLabel = (type: string) => {
                if (type === 'BEFORE_IMAGE') return 'BEFORE IMAGE';
                if (type === 'AFTER_IMAGE') return 'AFTER IMAGE / RESOLUTION EVIDENCE';
                if (type === 'VOICE_NOTE') return 'VOICE NOTE';
                return type.replace(/_/g, ' ');
              };

              return (
                <div key={ev.evidence_id} className="bg-white border border-slate-200 rounded-xl p-4 space-y-3 shadow-sm flex flex-col justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-[10px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded ${
                          ev.evidence_type === 'BEFORE_IMAGE'
                            ? 'bg-amber-100 text-amber-900 border border-amber-200'
                            : ev.evidence_type === 'AFTER_IMAGE'
                            ? 'bg-emerald-100 text-emerald-900 border border-emerald-200'
                            : 'bg-blue-100 text-blue-900 border border-blue-200'
                        }`}
                      >
                        {getEvidenceLabel(ev.evidence_type)}
                      </span>
                      <span
                        className={`text-[10px] font-bold ${
                          ev.verification_status === 'APPROVED' || (ev.verification_status as string) === 'VERIFIED'
                            ? 'text-emerald-600'
                            : ev.verification_status === 'REJECTED'
                            ? 'text-rose-600'
                            : 'text-amber-600'
                        }`}
                      >
                        {ev.verification_status}
                      </span>
                    </div>

                    {/* Media Display */}
                    {mediaUrl ? (
                      isImage ? (
                        <EvidenceImagePreview mediaUrl={mediaUrl} fileName={ev.file_name} />
                      ) : isAudio ? (
                        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 space-y-1">
                          <div className="flex items-center gap-1.5 text-xs text-indigo-700 font-semibold">
                            <Volume2 className="w-4 h-4" /> Audio Recording
                          </div>
                          <audio controls src={mediaUrl} className="w-full h-8" />
                        </div>
                      ) : (
                        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 flex items-center gap-2 text-xs text-slate-600">
                          <FileText className="w-4 h-4 text-slate-400" />
                          <span className="truncate">{ev.file_name}</span>
                        </div>
                      )
                    ) : (
                      <div className="bg-slate-50 border border-slate-200 rounded-lg h-44 flex flex-col items-center justify-center text-xs text-slate-500">
                        <ImageIcon className="w-5 h-5 text-slate-400 mb-1" />
                        <span>Preview unavailable</span>
                      </div>
                    )}

                    <p className="text-xs text-slate-700 font-mono truncate pt-1">{ev.file_name}</p>
                  </div>

                  <div className="flex justify-between items-center text-[11px] text-slate-500 border-t border-slate-100 pt-2 mt-auto">
                    <span>
                      Uploaded by: <strong className="text-slate-700 font-medium">{ev.uploaded_by}</strong>
                    </span>
                    {ev.uploaded_at && (
                      <span className="text-[10px] text-slate-400 font-mono">
                        {new Date(ev.uploaded_at).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Reopen Action Box */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm">
        <div>
          <h4 className="font-bold text-slate-900 text-sm">Dissatisfied with resolution?</h4>
          <p className="text-xs text-slate-600">You can reopen this ticket if the issue persists on the ground.</p>
        </div>

        <button
          onClick={() => setShowReopenModal(true)}
          className="px-5 py-2.5 rounded-xl bg-blue-700 hover:bg-blue-800 text-white text-xs font-semibold flex items-center gap-1.5 transition-all shadow-md"
        >
          <RotateCcw className="w-4 h-4" /> Reopen Ticket
        </button>
      </div>

      {/* Reopen Modal */}
      {showReopenModal && (
        <div className="fixed inset-0 bg-white/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <RotateCcw className="w-5 h-5 text-blue-600" /> Reopen Issue
            </h3>
            <p className="text-xs text-slate-600">
              Please specify why you are reopening this issue. This will trigger auto-escalation if policy thresholds are exceeded.
            </p>

            <textarea
              value={reopenReason}
              onChange={(e) => setReopenReason(e.target.value)}
              placeholder="e.g. The pothole was only partially filled and broke open again during rainfall."
              rows={4}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg p-3 text-slate-900 text-xs focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
            />

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setShowReopenModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-50 text-slate-700 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={() => reopenMutation.mutate(reopenReason || 'Dissatisfied with resolution work')}
                className="px-5 py-2 rounded-xl bg-blue-700 hover:bg-blue-800 text-white text-xs font-semibold shadow-sm"
              >
                Submit Reopen Request
              </button>
            </div>
          </div>
        </div>
      )}
      </>
      )}
    </div>
  );
};
