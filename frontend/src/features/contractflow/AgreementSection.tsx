import { useEffect, useState, type FormEvent } from 'react';
import { ApiError } from '../../services/api.ts';
import { contractflowService } from '../../services/contractflowService.ts';
import type {
  AgreementBundleResponse,
  AgreementStatus,
  ContractFlowOverview,
  Milestone,
  PaymentArrangement,
  Project,
} from '../../types/index.ts';

interface AgreementSectionProps {
  project: Project;
  currentUserRole: 'client' | 'freelancer';
  milestones: Milestone[];
  agreementBundle: AgreementBundleResponse | null;
  overview: ContractFlowOverview | null;
  loading: boolean;
  onRefresh: () => void;
}

function getAgreementBadge(status: AgreementStatus) {
  switch (status) {
    case 'active':
    case 'approved':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    case 'sent_for_review':
      return 'bg-blue-50 text-blue-700 border-blue-200';
    case 'changes_requested':
      return 'bg-amber-50 text-amber-800 border-amber-200';
    case 'cancelled':
      return 'bg-slate-100 text-slate-500 border-slate-200';
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200';
  }
}

export function AgreementSection({
  project,
  currentUserRole,
  milestones,
  agreementBundle,
  overview,
  loading,
  onRefresh,
}: AgreementSectionProps) {
  const isClient = currentUserRole === 'client';
  const current = agreementBundle?.currentAgreement ?? null;
  const approvals = agreementBundle?.approvals ?? [];

  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState('');
  const [scopeOfWork, setScopeOfWork] = useState('');
  const [deliverablesText, setDeliverablesText] = useState('');
  const [acceptanceCriteria, setAcceptanceCriteria] = useState('');
  const [paymentArrangement, setPaymentArrangement] = useState<PaymentArrangement>('milestone_prepayment');
  const [totalAmount, setTotalAmount] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [reviewPeriodDays, setReviewPeriodDays] = useState(3);
  const [revisionLimit, setRevisionLimit] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [additionalTerms, setAdditionalTerms] = useState('');
  const [aiArtifactNote, setAiArtifactNote] = useState<string | null>(null);
  const [isAiSeeded, setIsAiSeeded] = useState(false);

  const [saving, setSaving] = useState(false);
  const [generatingAi, setGeneratingAi] = useState(false);
  const [submittingReview, setSubmittingReview] = useState(false);
  const [deciding, setDeciding] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectNotes, setRejectNotes] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [showVersions, setShowVersions] = useState(false);

  const syncFormFromState = () => {
    if (current) {
      setTitle(current.title);
      setScopeOfWork(current.scopeOfWork || '');
      setDeliverablesText(current.deliverablesText || '');
      setAcceptanceCriteria(current.acceptanceCriteria || '');
      setPaymentArrangement(current.paymentArrangement);
      setTotalAmount(String(current.totalAmount));
      setCurrency(current.currency);
      setReviewPeriodDays(current.reviewPeriodDays);
      setRevisionLimit(current.revisionLimit !== undefined ? String(current.revisionLimit) : '');
      setStartDate(current.startDate || '');
      setEndDate(current.endDate || '');
      setAdditionalTerms(current.additionalTerms || '');
      setIsAiSeeded(current.isAiGenerated);
    } else {
      setTitle(`${project.title} — Service Agreement`);
      setScopeOfWork(project.description || '');
      setDeliverablesText(
        milestones
          .map((m, i) => `${i + 1}. ${m.title}${m.description ? `: ${m.description}` : ''} (Due ${m.dueDate || 'TBD'})`)
          .join('\n')
      );
      setAcceptanceCriteria('');
      setPaymentArrangement(project.paymentArrangement || 'milestone_prepayment');
      setTotalAmount(project.totalBudget ? String(project.totalBudget) : '');
      setCurrency(project.currency || 'USD');
      setReviewPeriodDays(project.reviewPeriodDays || 3);
      setRevisionLimit('');
      setStartDate(new Date(project.createdAt).toISOString().slice(0, 10));
      const latestMilestoneDate = milestones
        .map((m) => m.dueDate)
        .filter((d): d is string => Boolean(d))
        .sort()
        .slice(-1)[0];
      setEndDate(latestMilestoneDate || '');
      setAdditionalTerms('');
      setIsAiSeeded(false);
    }
  };

  useEffect(() => {
    if (!editing) {
      syncFormFromState();
    }
  }, [current?.id, current?.updatedAt, project.id, milestones.length]);

  const missingPrereqs: string[] = [];
  if (!project.clientId || !project.freelancerId) {
    missingPrereqs.push('Both client and freelancer must be members of the project.');
  }
  if (!project.totalBudget || project.totalBudget <= 0) {
    missingPrereqs.push('A positive project budget is required.');
  }
  if (milestones.length === 0 || milestones.some((m) => !m.dueDate)) {
    missingPrereqs.push('At least one planned milestone with an explicit due date is required.');
  }
  const prereqsMet = missingPrereqs.length === 0;

  const handleGenerateAiDraft = async () => {
    setError(null);
    setSuccessMsg(null);
    setGeneratingAi(true);
    try {
      const artifact: any = await contractflowService.generateAgreementDraft(project.id, project.sourceVersion);
      const payload = typeof artifact.payload_json === 'string' ? JSON.parse(artifact.payload_json) : artifact.payload_json;
      const sections: Array<{ title: string; paragraphs: string[] }> = payload?.sections || [];
      const scopeSection = sections.find((s) => s.title.toLowerCase().includes('scope'));
      const delivSection = sections.find((s) => s.title.toLowerCase().includes('deliverable'));
      const timelineSection = sections.find((s) => s.title.toLowerCase().includes('milestone'));
      const compSection = sections.find((s) => s.title.toLowerCase().includes('compensation'));

      setTitle(`${project.title} — Agreement Draft`);
      if (scopeSection) setScopeOfWork(scopeSection.paragraphs.join('\n\n'));
      if (delivSection) setDeliverablesText(delivSection.paragraphs.join('\n'));
      if (timelineSection || compSection) {
        setAdditionalTerms(
          [...(timelineSection?.paragraphs || []), ...(compSection?.paragraphs || [])].join('\n')
        );
      }
      setIsAiSeeded(true);
      setAiArtifactNote(`Seeded from ContractFlow AI artifact ${artifact.artifact_id} (rev ${artifact.artifact_version}). Review and edit before submitting.`);
      setEditing(true);
      onRefresh();
    } catch (err: unknown) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'AI agreement generation is currently unavailable. You can still compose and edit the draft below.'
      );
    } finally {
      setGeneratingAi(false);
    }
  };

  const handleSaveDraft = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    const parsedAmount = Number(totalAmount);
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setError('Agreement total amount must be a positive number.');
      return;
    }

    setSaving(true);
    try {
      await contractflowService.saveAgreementDraft(project.id, {
        title: title.trim(),
        scopeOfWork: scopeOfWork.trim(),
        deliverablesText: deliverablesText.trim() || undefined,
        acceptanceCriteria: acceptanceCriteria.trim() || undefined,
        paymentArrangement,
        totalAmount: parsedAmount,
        currency,
        revisionLimit: revisionLimit.trim() !== '' ? parseInt(revisionLimit, 10) : null,
        reviewPeriodDays,
        startDate: startDate || null,
        endDate: endDate || null,
        additionalTerms: additionalTerms.trim() || undefined,
        isAiGenerated: isAiSeeded,
        aiSummary: aiArtifactNote || undefined,
      });
      setEditing(false);
      setSuccessMsg('Agreement draft saved.');
      onRefresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Failed to save agreement draft.');
    } finally {
      setSaving(false);
    }
  };

  const handleSubmitForReview = async () => {
    if (!current) return;
    setError(null);
    setSuccessMsg(null);
    setSubmittingReview(true);
    try {
      await contractflowService.submitAgreementForReview(
        project.id,
        current.id,
        current.versionNumber,
        current.contentDigest
      );
      setSuccessMsg(`Agreement revision v${current.versionNumber} submitted for dual-party review.`);
      onRefresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Failed to submit agreement for review.');
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleDecision = async (decision: 'APPROVE' | 'REJECT') => {
    if (!current) return;
    if (decision === 'REJECT' && !rejectNotes.trim()) {
      setError('Please provide clear notes explaining what changes are requested.');
      return;
    }
    setError(null);
    setSuccessMsg(null);
    setDeciding(true);
    try {
      await contractflowService.decideAgreement(project.id, current.id, {
        decision,
        expectedVersion: current.versionNumber,
        expectedDigest: current.contentDigest,
        notes: decision === 'REJECT' ? rejectNotes.trim() : undefined,
      });
      setRejectOpen(false);
      setRejectNotes('');
      setSuccessMsg(
        decision === 'APPROVE'
          ? 'Your approval for this agreement revision has been recorded.'
          : 'Changes requested. The client can update and re-submit a revised draft.'
      );
      onRefresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Failed to record decision.');
    } finally {
      setDeciding(false);
    }
  };

  const currentApprovals = current ? approvals.filter((a) => a.agreementId === current.id) : [];
  const hasUserApprovedCurrent = current
    ? isClient
      ? Boolean(current.clientApprovedAt)
      : Boolean(current.freelancerApprovedAt)
    : false;
  const canDecideCurrent = Boolean(current && current.status === 'sent_for_review' && !hasUserApprovedCurrent);
  const canEditDraft = Boolean(
    isClient && (!current || ['draft', 'changes_requested', 'sent_for_review'].includes(current.status)) && project.status !== 'cancelled' && project.status !== 'completed'
  );

  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm animate-pulse space-y-3">
        <div className="h-4 bg-slate-200 rounded w-1/3" />
        <div className="h-24 bg-slate-100 rounded" />
      </div>
    );
  }

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-base font-bold text-slate-900">Initial Project Agreement</h3>
            {current && (
              <>
                <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border capitalize ${getAgreementBadge(current.status)}`}>
                  {current.status.replace(/_/g, ' ')}
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                  v{current.versionNumber}
                </span>
              </>
            )}
          </div>
          <p className="text-xs text-slate-500">
            Both client and freelancer must approve the exact same agreement revision before activating the baseline for scope amendments.
          </p>
        </div>

        {canEditDraft && !editing && (
          <div className="flex items-center gap-2 shrink-0 flex-wrap">
            {prereqsMet && (
              <button
                type="button"
                onClick={handleGenerateAiDraft}
                disabled={generatingAi}
                className="px-3 py-1.5 border border-brand-200 bg-brand-50 hover:bg-brand-100 text-brand-800 text-xs font-semibold rounded-lg transition-colors disabled:opacity-50"
              >
                {generatingAi ? 'Generating AI Draft...' : '✨ Generate AI Draft'}
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                syncFormFromState();
                setEditing(true);
              }}
              className="px-3.5 py-1.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold rounded-lg transition-colors"
            >
              {current ? 'Edit Agreement Draft' : 'Create Agreement Draft'}
            </button>
          </div>
        )}
      </div>

      {/* Prerequisite Warning */}
      {!prereqsMet && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-1.5 text-xs text-amber-900">
          <p className="font-bold">Agreement Setup Required</p>
          <ul className="list-disc pl-5 space-y-0.5 text-amber-800">
            {missingPrereqs.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          {overview && !overview.groq_enabled && (
            <p className="text-[11px] text-amber-700 pt-1">
              Note: AI ContractFlow drafting is currently disabled; manual structured drafting remains available once prerequisites are complete.
            </p>
          )}
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">{error}</div>
      )}
      {successMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800">{successMsg}</div>
      )}

      {/* Editable Draft Form (Client Only) */}
      {editing && isClient && (
        <form onSubmit={handleSaveDraft} className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              {current?.status === 'sent_for_review'
                ? `Create Revision v${current.versionNumber + 1}`
                : current
                ? `Edit Draft (v${current.versionNumber})`
                : 'New Agreement Draft (v1)'}
            </h4>
            <button type="button" onClick={() => setEditing(false)} className="text-xs text-slate-500 hover:text-slate-800">
              Cancel
            </button>
          </div>

          {aiArtifactNote && (
            <div className="p-2.5 bg-blue-50 border border-blue-200 rounded-lg text-[11px] text-blue-800">
              {aiArtifactNote}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="sm:col-span-2 space-y-1">
              <label className="block text-[11px] font-semibold text-slate-700">Agreement Title *</label>
              <input
                type="text"
                required
                maxLength={200}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900"
              />
            </div>

            <div className="sm:col-span-2 space-y-1">
              <label className="block text-[11px] font-semibold text-slate-700">Scope of Work *</label>
              <textarea
                rows={3}
                required
                value={scopeOfWork}
                onChange={(e) => setScopeOfWork(e.target.value)}
                className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900"
              />
            </div>

            <div className="sm:col-span-2 space-y-1">
              <label className="block text-[11px] font-semibold text-slate-700">Deliverables Summary</label>
              <textarea
                rows={3}
                value={deliverablesText}
                onChange={(e) => setDeliverablesText(e.target.value)}
                className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900"
              />
            </div>

            <div className="sm:col-span-2 space-y-1">
              <label className="block text-[11px] font-semibold text-slate-700">Acceptance Criteria</label>
              <textarea
                rows={2}
                value={acceptanceCriteria}
                onChange={(e) => setAcceptanceCriteria(e.target.value)}
                placeholder="Explicit objective criteria for accepting deliverables..."
                className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-[11px] font-semibold text-slate-700">Payment Arrangement *</label>
              <select
                value={paymentArrangement}
                onChange={(e) => setPaymentArrangement(e.target.value as PaymentArrangement)}
                className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900"
              >
                <option value="milestone_prepayment">Milestone Prepayment</option>
                <option value="payment_after_approval">Payment After Approval</option>
                <option value="upfront">Full Upfront</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <label className="block text-[11px] font-semibold text-slate-700">Total Amount *</label>
                <input
                  type="number"
                  required
                  min="0.01"
                  step="0.01"
                  value={totalAmount}
                  onChange={(e) => setTotalAmount(e.target.value)}
                  className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-[11px] font-semibold text-slate-700">Currency *</label>
                <input
                  type="text"
                  required
                  maxLength={3}
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                  className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="block text-[11px] font-semibold text-slate-700">Review Period (Days) *</label>
              <input
                type="number"
                required
                min="1"
                value={reviewPeriodDays}
                onChange={(e) => setReviewPeriodDays(parseInt(e.target.value, 10) || 1)}
                className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-[11px] font-semibold text-slate-700">Revision Limit (Optional)</label>
              <input
                type="number"
                min="0"
                value={revisionLimit}
                onChange={(e) => setRevisionLimit(e.target.value)}
                placeholder="e.g. 2"
                className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-[11px] font-semibold text-slate-700">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-[11px] font-semibold text-slate-700">Target End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900"
              />
            </div>

            <div className="sm:col-span-2 space-y-1">
              <label className="block text-[11px] font-semibold text-slate-700">Additional Terms</label>
              <textarea
                rows={2}
                value={additionalTerms}
                onChange={(e) => setAdditionalTerms(e.target.value)}
                className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setEditing(false)}
              disabled={saving}
              className="px-3.5 py-1.5 border border-slate-300 bg-white text-slate-700 text-xs font-semibold rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-1.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white text-xs font-semibold rounded-lg"
            >
              {saving ? 'Saving Draft...' : 'Save Agreement Draft'}
            </button>
          </div>
        </form>
      )}

      {/* Shared Agreement Preview & Review Card */}
      {!current && !editing ? (
        <div className="p-6 bg-slate-50 border border-dashed border-slate-300 rounded-xl text-center space-y-2">
          <p className="text-xs font-semibold text-slate-700">No Initial Agreement Draft Yet</p>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            {isClient
              ? 'Complete the project budget and planned milestones above, then compose or generate an agreement draft to share for review.'
              : 'Waiting for the client to draft and submit the initial agreement revision for your review.'}
          </p>
        </div>
      ) : current && !editing ? (
        <div className="space-y-4">
          {/* Party Approval Status Strip */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[10px] font-bold uppercase text-slate-400 block">Client Approval</span>
              <span className={`text-xs font-bold ${current.clientApprovedAt ? 'text-emerald-700' : 'text-slate-600'}`}>
                {current.clientApprovedAt
                  ? `✓ Approved (${new Date(current.clientApprovedAt).toLocaleDateString()})`
                  : 'Pending'}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[10px] font-bold uppercase text-slate-400 block">Freelancer Approval</span>
              <span className={`text-xs font-bold ${current.freelancerApprovedAt ? 'text-emerald-700' : 'text-slate-600'}`}>
                {current.freelancerApprovedAt
                  ? `✓ Approved (${new Date(current.freelancerApprovedAt).toLocaleDateString()})`
                  : 'Pending'}
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
              <span className="text-[10px] font-bold uppercase text-slate-400 block">Revision Digest (SHA-256)</span>
              <span className="text-[11px] font-mono text-slate-700 break-all" title={current.contentDigest}>
                {current.contentDigest.slice(0, 16)}...{current.contentDigest.slice(-8)}
              </span>
            </div>
          </div>

          {/* Agreement Terms View */}
          <div className="border border-slate-200 rounded-xl p-5 space-y-4 bg-slate-50/50">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <h4 className="text-sm font-bold text-slate-900">{current.title}</h4>
              <span className="text-xs font-bold text-slate-900">
                {current.currency} {Number(current.totalAmount).toLocaleString(undefined, { minimumFractionDigits: 2 })} ·{' '}
                <span className="capitalize font-medium text-slate-600">
                  {current.paymentArrangement.replace(/_/g, ' ')}
                </span>
              </span>
            </div>

            <div className="space-y-1">
              <span className="text-[10px] font-bold uppercase text-slate-400">Scope of Work</span>
              <p className="text-xs text-slate-700 whitespace-pre-wrap leading-relaxed">{current.scopeOfWork}</p>
            </div>

            {current.deliverablesText && (
              <div className="space-y-1">
                <span className="text-[10px] font-bold uppercase text-slate-400">Deliverables</span>
                <p className="text-xs text-slate-700 whitespace-pre-wrap leading-relaxed">{current.deliverablesText}</p>
              </div>
            )}

            {current.acceptanceCriteria && (
              <div className="space-y-1">
                <span className="text-[10px] font-bold uppercase text-slate-400">Acceptance Criteria</span>
                <p className="text-xs text-slate-700 whitespace-pre-wrap">{current.acceptanceCriteria}</p>
              </div>
            )}

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-slate-200/70 text-xs">
              <div>
                <span className="text-[10px] text-slate-400 block font-bold uppercase">Review Period</span>
                <span className="font-semibold text-slate-800">{current.reviewPeriodDays} day(s)</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 block font-bold uppercase">Revisions</span>
                <span className="font-semibold text-slate-800">
                  {current.revisionLimit !== undefined ? current.revisionLimit : 'Not specified'}
                </span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 block font-bold uppercase">Start Date</span>
                <span className="font-semibold text-slate-800">{current.startDate || 'Not specified'}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-400 block font-bold uppercase">End Date</span>
                <span className="font-semibold text-slate-800">{current.endDate || 'Not specified'}</span>
              </div>
            </div>

            {current.additionalTerms && (
              <div className="space-y-1 pt-2 border-t border-slate-200/70">
                <span className="text-[10px] font-bold uppercase text-slate-400">Additional Terms</span>
                <p className="text-xs text-slate-600 whitespace-pre-wrap">{current.additionalTerms}</p>
              </div>
            )}
          </div>

          {/* Client Submit for Review Action */}
          {isClient && ['draft', 'changes_requested'].includes(current.status) && (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-blue-50 border border-blue-200 rounded-xl">
              <p className="text-xs text-blue-900">
                Ready for both parties to review? Submitting freezes revision <strong>v{current.versionNumber}</strong> for approval.
              </p>
              <button
                type="button"
                onClick={handleSubmitForReview}
                disabled={submittingReview || !prereqsMet}
                className="px-4 py-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shrink-0"
              >
                {submittingReview ? 'Submitting...' : 'Submit Revision for Review'}
              </button>
            </div>
          )}

          {/* Dual-Party Decision Controls */}
          {canDecideCurrent && (
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-bold text-slate-900">
                    Your Review Decision Required (Revision v{current.versionNumber})
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Approving records consent to this exact digest. It does not release funds or create an escrow/wet signature.
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => setRejectOpen(!rejectOpen)}
                    disabled={deciding}
                    className="px-3.5 py-2 border border-rose-200 text-rose-700 hover:bg-rose-50 text-xs font-semibold rounded-lg"
                  >
                    Request Changes
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDecision('APPROVE')}
                    disabled={deciding}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white text-xs font-semibold rounded-lg"
                  >
                    {deciding ? 'Recording...' : 'Approve Agreement'}
                  </button>
                </div>
              </div>

              {rejectOpen && (
                <div className="space-y-2 pt-2 border-t border-slate-200">
                  <textarea
                    rows={2}
                    value={rejectNotes}
                    onChange={(e) => setRejectNotes(e.target.value)}
                    placeholder="Specify requested changes..."
                    className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900"
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setRejectOpen(false)}
                      className="px-3 py-1 text-xs text-slate-600"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDecision('REJECT')}
                      disabled={deciding}
                      className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg"
                    >
                      Submit Change Request
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {current.status === 'active' && (
            <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-900">
              <strong>Both Parties Approved (Active Baseline):</strong> Revision v{current.versionNumber} is now locked in{' '}
              <code>public.agreements</code>. Subsequent scope changes require a ContractFlow amendment. Approval does not execute payments or constitute a legally executed signature.
            </div>
          )}

          {/* Decision Log & Revision History */}
          {currentApprovals.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-bold uppercase text-slate-400">Approval Audit Log (v{current.versionNumber})</span>
              <div className="space-y-1">
                {currentApprovals.map((a) => (
                  <div key={a.id} className="text-xs text-slate-600 flex items-center justify-between bg-slate-50 px-3 py-1.5 rounded-lg">
                    <span>
                      <strong className="capitalize text-slate-800">{a.role}</strong>{' '}
                      {a.action === 'approved' ? 'approved' : 'requested changes'}
                      {a.notes ? ` — "${a.notes}"` : ''}
                    </span>
                    <span className="text-[10px] text-slate-400">{new Date(a.createdAt).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(agreementBundle?.versions.length ?? 0) > 1 && (
            <div className="pt-1">
              <button
                type="button"
                onClick={() => setShowVersions(!showVersions)}
                className="text-xs font-semibold text-brand-600 hover:text-brand-700"
              >
                {showVersions ? 'Hide' : 'Show'} Prior Revisions ({(agreementBundle?.versions.length ?? 1) - 1})
              </button>
              {showVersions && (
                <div className="mt-2 space-y-2">
                  {agreementBundle!.versions
                    .filter((v) => v.id !== current.id)
                    .map((v) => (
                      <div key={v.id} className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs flex items-center justify-between">
                        <div>
                          <span className="font-bold text-slate-800">v{v.versionNumber} — {v.title}</span>
                          <span className="block text-[10px] font-mono text-slate-400">{v.contentDigest}</span>
                        </div>
                        <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                          {v.status.replace(/_/g, ' ')}
                        </span>
                      </div>
                    ))}
                </div>
              )}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

