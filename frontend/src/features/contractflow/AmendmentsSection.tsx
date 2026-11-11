import { useState, type FormEvent } from 'react';
import { ApiError } from '../../services/api.ts';
import { contractflowService } from '../../services/contractflowService.ts';
import type {
  AgreementWithDigest,
  AmendmentApprovalState,
  ContractFlowArtifactItem,
  ContractFlowAuditEvent,
  ContractFlowOverview,
  Project,
} from '../../types/index.ts';

interface AmendmentsSectionProps {
  project: Project;
  currentUserRole: 'client' | 'freelancer';
  currentAgreement: AgreementWithDigest | null;
  overview: ContractFlowOverview | null;
  onRefresh: () => void;
}

function getAmendmentStateBadge(state: AmendmentApprovalState | 'UNREGISTERED') {
  switch (state) {
    case 'BOTH_APPROVED':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    case 'PARTIALLY_APPROVED':
      return 'bg-blue-50 text-blue-700 border-blue-200';
    case 'PENDING_REVIEW':
      return 'bg-amber-50 text-amber-800 border-amber-200';
    case 'REJECTED':
      return 'bg-rose-50 text-rose-700 border-rose-200';
    case 'SUPERSEDED':
      return 'bg-slate-100 text-slate-500 border-slate-200';
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200';
  }
}

export function AmendmentsSection({
  project,
  currentUserRole,
  currentAgreement,
  overview,
  onRefresh,
}: AmendmentsSectionProps) {
  const userPartyRole: 'CLIENT' | 'FREELANCER' = currentUserRole === 'client' ? 'CLIENT' : 'FREELANCER';

  const [scopeRequest, setScopeRequest] = useState('');
  const [assessing, setAssessing] = useState(false);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Per-amendment review gate checkboxes & rejection notes & audit history cache
  const [humanChecked, setHumanChecked] = useState<Record<string, boolean>>({});
  const [semanticChecked, setSemanticChecked] = useState<Record<string, boolean>>({});
  const [rejectReason, setRejectReason] = useState<Record<string, string>>({});
  const [historyMap, setHistoryMap] = useState<Record<string, ContractFlowAuditEvent[]>>({});
  const [openHistoryId, setOpenHistoryId] = useState<string | null>(null);

  const hasActiveAgreement = Boolean(overview?.has_active_agreement || currentAgreement?.status === 'active');
  const artifacts = overview?.artifacts ?? [];
  const assessments = artifacts.filter((a) => a.kind === 'ASSESSMENT');
  const amendments = artifacts.filter((a) => a.kind === 'AMENDMENT');

  const handleAssessScope = async (e: FormEvent) => {
    e.preventDefault();
    if (!scopeRequest.trim()) return;
    setError(null);
    setNotice(null);
    setAssessing(true);
    try {
      await contractflowService.assessScope(project.id, project.sourceVersion, scopeRequest.trim());
      setScopeRequest('');
      setNotice('Scope change assessment recorded.');
      onRefresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Failed to assess scope change.');
    } finally {
      setAssessing(false);
    }
  };

  const handleIssueAssessmentReview = async (item: ContractFlowArtifactItem) => {
    setError(null);
    setNotice(null);
    setBusyKey(`assess-rev-${item.artifact_id}`);
    try {
      const receipt = await contractflowService.issueAssessmentReview(
        project.id,
        item.artifact_id,
        item.revision,
        item.content_digest
      );
      setNotice(`V4 assessment review receipt issued (${receipt.review_reference}).`);
      onRefresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Failed to issue assessment review receipt.');
    } finally {
      setBusyKey(null);
    }
  };

  const handleGenerateAmendment = async (assessmentId: string, reviewReference: string) => {
    setError(null);
    setNotice(null);
    setBusyKey(`gen-amend-${assessmentId}`);
    try {
      await contractflowService.generateAmendment(project.id, project.sourceVersion, assessmentId, reviewReference);
      setNotice('Proposed amendment draft generated. Human + semantic review is required before registration.');
      onRefresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Failed to generate amendment proposal.');
    } finally {
      setBusyKey(null);
    }
  };

  const handleIssueAmendmentReview = async (item: ContractFlowArtifactItem) => {
    const key = `${item.artifact_id}:${item.revision}`;
    if (!humanChecked[key] || !semanticChecked[key]) {
      setError('Both separate human review and semantic review confirmations are required.');
      return;
    }
    setError(null);
    setNotice(null);
    setBusyKey(`grant-${key}`);
    try {
      await contractflowService.issueAmendmentReview(item.artifact_id, item.revision, item.content_digest);
      setNotice('Amendment review grant recorded.');
      onRefresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Failed to issue amendment review grant.');
    } finally {
      setBusyKey(null);
    }
  };

  const handleRevokeReview = async (amendmentId: string, reviewId: string) => {
    const reason = window.prompt('Enter revocation reason for this review grant:');
    if (!reason || !reason.trim()) return;
    setError(null);
    setBusyKey(`revoke-${reviewId}`);
    try {
      await contractflowService.revokeAmendmentReview(amendmentId, reviewId, reason.trim());
      setNotice('Review grant revoked.');
      onRefresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Failed to revoke review grant.');
    } finally {
      setBusyKey(null);
    }
  };

  const handleRegisterAmendment = async (item: ContractFlowArtifactItem) => {
    setError(null);
    setNotice(null);
    setBusyKey(`reg-${item.artifact_id}-${item.revision}`);
    try {
      await contractflowService.registerAmendment(item.artifact_id, item.revision, item.content_digest);
      setNotice(`Amendment v${item.revision} registered for dual-party review (PENDING_REVIEW).`);
      onRefresh();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Failed to register amendment.');
    } finally {
      setBusyKey(null);
    }
  };

  const handleAmendmentDecision = async (item: ContractFlowArtifactItem, decision: 'APPROVE' | 'REJECT') => {
    const key = `${item.artifact_id}:${item.revision}`;
    const approvalDigest = item.approval_head?.approval_digest || item.approval_digest;
    if (!approvalDigest) {
      setError('Missing canonical approval digest for this revision.');
      return;
    }
    const reasonText = rejectReason[key]?.trim();
    if (decision === 'REJECT' && !reasonText) {
      setError('Please enter a rejection reason.');
      return;
    }
    setError(null);
    setNotice(null);
    setBusyKey(`dec-${key}`);
    try {
      const idempotencyKey = `ui-${userPartyRole.toLowerCase()}-${item.artifact_id.slice(0, 8)}-v${item.revision}-${Date.now()}`;
      const status = await contractflowService.submitAmendmentDecision(item.artifact_id, {
        decision,
        expected_version: item.revision,
        expected_digest: approvalDigest,
        idempotency_key: idempotencyKey,
        ...(decision === 'REJECT' ? { rejection_reason: reasonText } : {}),
      });
      setNotice(`Decision recorded: amendment state is now ${status.state}.`);
      onRefresh();
      if (openHistoryId === item.artifact_id) {
        const hist = await contractflowService.getAmendmentHistory(item.artifact_id);
        setHistoryMap((prev) => ({ ...prev, [item.artifact_id]: hist }));
      }
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Failed to submit amendment decision.');
    } finally {
      setBusyKey(null);
    }
  };

  const toggleHistory = async (amendmentId: string) => {
    if (openHistoryId === amendmentId) {
      setOpenHistoryId(null);
      return;
    }
    setOpenHistoryId(amendmentId);
    try {
      const hist = await contractflowService.getAmendmentHistory(amendmentId);
      setHistoryMap((prev) => ({ ...prev, [amendmentId]: hist }));
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Failed to load amendment history.');
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-5">
      <div className="border-b border-slate-100 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="text-base font-bold text-slate-900">Scope Changes & ContractFlow Amendments</h3>
          <p className="text-xs text-slate-500">
            V3 Scope Assessment &rarr; V4 Human Review & Amendment Proposal &rarr; V5 Dual-Party Approval & Audit History.
          </p>
        </div>
        {overview && (
          <span
            className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${
              overview.groq_enabled
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-slate-100 text-slate-600 border-slate-200'
            }`}
          >
            AI Provider: {overview.groq_enabled ? 'Enabled' : 'Disabled'}
          </span>
        )}
      </div>

      {error && <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">{error}</div>}
      {notice && <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800">{notice}</div>}

      {!hasActiveAgreement ? (
        <div className="p-5 bg-slate-50 border border-dashed border-slate-300 rounded-xl text-center space-y-1">
          <p className="text-xs font-semibold text-slate-700">Amendments Locked Until Initial Agreement Is Active</p>
          <p className="text-[11px] text-slate-500">
            Both parties must approve the initial project agreement before scope-change assessments or amendments can be created.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Scope Change Assessment Request Form */}
          <form onSubmit={handleAssessScope} className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
            <label htmlFor="scopeChangeInput" className="block text-xs font-bold text-slate-800">
              Assess New Scope Change Request
            </label>
            <textarea
              id="scopeChangeInput"
              rows={2}
              required
              value={scopeRequest}
              onChange={(e) => setScopeRequest(e.target.value)}
              placeholder="Describe the requested feature, timeline shift, or deliverable modification..."
              className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] text-slate-500">
                Assessed against active agreement v{currentAgreement?.versionNumber ?? 1}.
              </span>
              <button
                type="submit"
                disabled={assessing || !scopeRequest.trim()}
                className="px-4 py-1.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg"
              >
                {assessing ? 'Assessing...' : 'Run Scope Assessment'}
              </button>
            </div>
          </form>

          {/* Stored Scope Assessments */}
          {assessments.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Scope Change Assessments ({assessments.length})
              </h4>
              {assessments.map((item) => {
                const analysis = item.payload?.analysis || {};
                const classification = analysis.classification || 'UNKNOWN';
                const reviews = (item.assessment_reviews || []).filter((r) => !r.revoked);
                const latestReview = reviews[0];
                return (
                  <div key={`${item.artifact_id}:${item.revision}`} className="border border-slate-200 rounded-xl p-4 space-y-3 bg-slate-50/40">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-brand-50 text-brand-800 border border-brand-200">
                          {classification}
                        </span>
                        <span className="text-[11px] text-slate-500 font-mono">
                          {item.artifact_id.slice(0, 8)} · rev {item.revision}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-400">
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                    </div>

                    <p className="text-xs text-slate-700 leading-relaxed">{analysis.explanation}</p>
                    <p className="text-[11px] text-slate-500">
                      Request: <em>"{item.payload?.input_snapshot?.client_request}"</em>
                    </p>

                    {classification === 'OUT_OF_SCOPE' && (
                      <div className="pt-2 border-t border-slate-200/70 flex flex-wrap items-center justify-between gap-2">
                        {!latestReview ? (
                          <>
                            <span className="text-[11px] text-amber-800">
                              Human review verification required before generating an amendment proposal.
                            </span>
                            <button
                              type="button"
                              onClick={() => handleIssueAssessmentReview(item)}
                              disabled={busyKey === `assess-rev-${item.artifact_id}`}
                              className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold rounded-lg"
                            >
                              {busyKey === `assess-rev-${item.artifact_id}`
                                ? 'Recording...'
                                : 'Confirm Human Assessment Review'}
                            </button>
                          </>
                        ) : (
                          <>
                            <span className="text-[11px] text-emerald-700 font-semibold">
                              ✓ V4 Receipt Issued ({latestReview.review_reference.slice(0, 20)}...)
                            </span>
                            <button
                              type="button"
                              onClick={() => handleGenerateAmendment(item.artifact_id, latestReview.review_reference)}
                              disabled={busyKey === `gen-amend-${item.artifact_id}`}
                              className="px-3.5 py-1.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold rounded-lg"
                            >
                              {busyKey === `gen-amend-${item.artifact_id}`
                                ? 'Generating...'
                                : 'Generate Proposed Amendment'}
                            </button>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Proposed Amendments & Dual-Party Workflow */}
          {amendments.length === 0 ? (
            <p className="text-xs text-slate-400 text-center py-2">No amendment proposals recorded yet.</p>
          ) : (
            <div className="space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Amendment Proposals ({amendments.length})
              </h4>
              {amendments.map((item) => {
                const key = `${item.artifact_id}:${item.revision}`;
                const head = item.approval_head;
                const state: AmendmentApprovalState | 'UNREGISTERED' = head?.state || 'UNREGISTERED';
                const activeReviews = (item.reviews || []).filter(
                  (r) => !r.revoked && new Date(r.expires_at).getTime() > Date.now()
                );
                const hasValidGrant = activeReviews.length > 0;
                const decisions = item.decisions || [];
                const clientDecided = decisions.some((d) => d.role === 'CLIENT');
                const freelancerDecided = decisions.some((d) => d.role === 'FREELANCER');
                const userAlreadyDecided = decisions.some((d) => d.role === userPartyRole);
                const canVote =
                  (state === 'PENDING_REVIEW' || state === 'PARTIALLY_APPROVED') &&
                  hasValidGrant &&
                  !userAlreadyDecided;
                const origFacts = item.payload?.original_facts;

                return (
                  <div key={key} className="border border-slate-200 rounded-xl p-5 space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${getAmendmentStateBadge(state)}`}>
                          {state}
                        </span>
                        <span className="text-xs font-bold text-slate-900">
                          Amendment {item.artifact_id.slice(0, 8)} · Rev {item.revision}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => toggleHistory(item.artifact_id)}
                        className="text-xs font-semibold text-brand-600 hover:text-brand-700"
                      >
                        {openHistoryId === item.artifact_id ? 'Hide Audit History' : 'View Audit History'}
                      </button>
                    </div>

                    <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg text-[11px] text-amber-900 font-semibold">
                      {item.payload?.notice || 'PROPOSED AMENDMENT — NOT EFFECTIVE UNTIL BOTH PARTIES APPROVE'}
                    </div>

                    {/* Side-by-side Original vs Proposed Comparison */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
                        <span className="text-[10px] font-bold uppercase text-slate-400">Original Baseline (v{item.payload?.original_agreement_version})</span>
                        <p className="text-slate-700"><strong>Scope:</strong> {origFacts?.scope}</p>
                        <p className="text-slate-700">
                          <strong>Budget:</strong> {origFacts?.currency} {origFacts?.budget} · <strong>Deadline:</strong> {origFacts?.deadline}
                        </p>
                      </div>
                      <div className="p-3 bg-blue-50/40 border border-blue-200 rounded-lg space-y-1">
                        <span className="text-[10px] font-bold uppercase text-blue-600">Proposed Changes</span>
                        <p className="text-slate-700"><strong>Timeline:</strong> {item.payload?.proposals?.timeline?.text}</p>
                        <p className="text-slate-700"><strong>Compensation:</strong> {item.payload?.proposals?.compensation?.text}</p>
                      </div>
                    </div>

                    {item.payload?.rendered_text && (
                      <details className="text-xs">
                        <summary className="cursor-pointer font-semibold text-slate-700">
                          View Rendered Amendment Proposal Text
                        </summary>
                        <pre className="mt-2 p-3 bg-slate-50 border border-slate-200 rounded-lg whitespace-pre-wrap text-[11px] text-slate-700 font-sans">
                          {item.payload.rendered_text}
                        </pre>
                      </details>
                    )}

                    <div className="text-[11px] font-mono text-slate-500 space-y-0.5">
                      <div>Artifact Digest: {item.content_digest}</div>
                      {item.approval_digest && <div>Approval Subject Digest: {item.approval_digest}</div>}
                    </div>

                    {/* Separate Human + Semantic Review Gate */}
                    <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2.5 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-800">Human & Semantic Review Gate</span>
                        <span className={`text-[11px] font-semibold ${hasValidGrant ? 'text-emerald-700' : 'text-amber-700'}`}>
                          {hasValidGrant ? 'Active Review Grant Present' : 'Review Grant Required'}
                        </span>
                      </div>

                      {activeReviews.map((rev) => (
                        <div key={rev.review_id} className="flex items-center justify-between bg-white border border-slate-200 px-3 py-2 rounded-lg text-[11px]">
                          <span>
                            Grant {rev.review_id.slice(0, 8)} · Human & Semantic verified · Expires {new Date(rev.expires_at).toLocaleString()}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleRevokeReview(item.artifact_id, rev.review_id)}
                            disabled={busyKey === `revoke-${rev.review_id}`}
                            className="text-rose-600 font-semibold hover:underline"
                          >
                            Revoke Grant
                          </button>
                        </div>
                      ))}

                      {!hasValidGrant && (
                        <div className="space-y-2 pt-1">
                          <label className="flex items-start gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={Boolean(humanChecked[key])}
                              onChange={(e) => setHumanChecked((p) => ({ ...p, [key]: e.target.checked }))}
                              className="mt-0.5"
                            />
                            <span>Human review confirmed: I have manually reviewed the amendment text and unresolved terms.</span>
                          </label>
                          <label className="flex items-start gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={Boolean(semanticChecked[key])}
                              onChange={(e) => setSemanticChecked((p) => ({ ...p, [key]: e.target.checked }))}
                              className="mt-0.5"
                            />
                            <span>Semantic review confirmed: Proposed wording matches the approved assessment and citations.</span>
                          </label>
                          <button
                            type="button"
                            onClick={() => handleIssueAmendmentReview(item)}
                            disabled={!humanChecked[key] || !semanticChecked[key] || busyKey === `grant-${key}`}
                            className="px-3.5 py-1.5 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-semibold rounded-lg"
                          >
                            {busyKey === `grant-${key}` ? 'Recording Review...' : 'Record Review Grant'}
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Registration Step */}
                    {state === 'UNREGISTERED' && (
                      <div className="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-xl text-xs">
                        <span className="text-blue-900">
                          Register revision v{item.revision} to initialize dual-party approval (PENDING_REVIEW).
                        </span>
                        <button
                          type="button"
                          onClick={() => handleRegisterAmendment(item)}
                          disabled={!hasValidGrant || busyKey === `reg-${item.artifact_id}-${item.revision}`}
                          className="px-3.5 py-1.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg"
                        >
                          Register Revision
                        </button>
                      </div>
                    )}

                    {/* Registered Approval Status & Voting */}
                    {state !== 'UNREGISTERED' && (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                            <span className="text-[10px] font-bold uppercase text-slate-400 block">Client Decision</span>
                            <span className="font-semibold text-slate-800">
                              {clientDecided
                                ? decisions.find((d) => d.role === 'CLIENT')?.decision
                                : 'Pending'}
                            </span>
                          </div>
                          <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                            <span className="text-[10px] font-bold uppercase text-slate-400 block">Freelancer Decision</span>
                            <span className="font-semibold text-slate-800">
                              {freelancerDecided
                                ? decisions.find((d) => d.role === 'FREELANCER')?.decision
                                : 'Pending'}
                            </span>
                          </div>
                        </div>

                        {canVote && (
                          <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                            <input
                              type="text"
                              value={rejectReason[key] || ''}
                              onChange={(e) => setRejectReason((p) => ({ ...p, [key]: e.target.value }))}
                              placeholder="Optional rejection reason (required if rejecting)"
                              className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs"
                            />
                            <div className="flex justify-end gap-2">
                              <button
                                type="button"
                                onClick={() => handleAmendmentDecision(item, 'REJECT')}
                                disabled={busyKey === `dec-${key}`}
                                className="px-3.5 py-1.5 border border-rose-200 text-rose-700 hover:bg-rose-50 text-xs font-semibold rounded-lg"
                              >
                                Reject Amendment
                              </button>
                              <button
                                type="button"
                                onClick={() => handleAmendmentDecision(item, 'APPROVE')}
                                disabled={busyKey === `dec-${key}`}
                                className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg"
                              >
                                Approve Amendment
                              </button>
                            </div>
                          </div>
                        )}

                        {state === 'BOTH_APPROVED' && (
                          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-[11px] text-emerald-900">
                            <strong>BOTH_APPROVED:</strong> Both parties have approved this amendment digest. Notice: BOTH_APPROVED does not trigger PayPal/escrow payment or execute a legal signature.
                          </div>
                        )}
                      </div>
                    )}

                    {/* Audit History Panel */}
                    {openHistoryId === item.artifact_id && (
                      <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs">
                        <span className="text-[10px] font-bold uppercase text-slate-500 block">
                          Append-Only Audit Trail
                        </span>
                        {(historyMap[item.artifact_id] || []).length === 0 ? (
                          <p className="text-[11px] text-slate-400">No audit events recorded yet (register revision first).</p>
                        ) : (
                          historyMap[item.artifact_id].map((ev) => (
                            <div key={ev.event_id} className="flex items-center justify-between text-[11px] bg-white px-3 py-1.5 rounded border border-slate-200">
                              <span>
                                <strong>Rev {ev.amendment_version}</strong> · {ev.role} · <strong>{ev.action}</strong>{' '}
                                ({ev.previous_state ?? 'NONE'} &rarr; {ev.new_state})
                              </span>
                              <span className="text-slate-400">{new Date(ev.timestamp).toLocaleString()}</span>
                            </div>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

