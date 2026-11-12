import { useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from '../../services/api.ts';
import { contractflowService } from '../../services/contractflowService.ts';
import { useRouter } from '../../lib/router.tsx';
import { MilestonesPanel } from '../contractflow/MilestonesPanel.tsx';
import { AgreementSection } from '../contractflow/AgreementSection.tsx';
import { AmendmentsSection } from '../contractflow/AmendmentsSection.tsx';
import { TasksView } from '../workbridge/TasksView.tsx';
import { DeliverablesView } from '../workbridge/DeliverablesView.tsx';
import { CollaborationView } from '../workbridge/CollaborationView.tsx';
import type {
  AgreementBundleResponse,
  ContractFlowOverview,
  InvitationResponse,
  ProjectDetail,
} from '../../types/index.ts';

interface ProjectDetailViewProps {
  projectId: string;
}

export function ProjectDetailView({ projectId }: ProjectDetailViewProps) {
  const { navigate } = useRouter();

  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Invitation Form State
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteMessage, setInviteMessage] = useState('');
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [latestInviteLink, setLatestInviteLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Cancellation & ContractFlow Workspace State
  const [cancelling, setCancelling] = useState(false);

  // WorkBridge Workspace Tab selection
  const [activeTab, setActiveTab] = useState<'overview' | 'tasks' | 'deliverables' | 'collaboration'>('overview');
  const [agreementBundle, setAgreementBundle] = useState<AgreementBundleResponse | null>(null);
  const [agreementLoading, setAgreementLoading] = useState(false);
  const [cfOverview, setCfOverview] = useState<ContractFlowOverview | null>(null);
  const [cfNotice, setCfNotice] = useState<string | null>(null);

  // Inline budget edit state (needed if project was created without a budget)
  const [editingBudget, setEditingBudget] = useState(false);
  const [budgetInput, setBudgetInput] = useState('');
  const [savingBudget, setSavingBudget] = useState(false);

  const fetchContractFlowState = async () => {
    setAgreementLoading(true);
    setCfNotice(null);
    const [agResult, ovResult] = await Promise.allSettled([
      contractflowService.getCurrentAgreement(projectId),
      contractflowService.getOverview(projectId),
    ]);
    if (agResult.status === 'fulfilled') {
      setAgreementBundle(agResult.value);
    }
    if (ovResult.status === 'fulfilled') {
      setCfOverview(ovResult.value);
    } else {
      const msg = ovResult.reason instanceof ApiError ? ovResult.reason.message : 'ContractFlow service unavailable';
      setCfNotice(msg);
    }
    setAgreementLoading(false);
  };

  const fetchProjectDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<ProjectDetail>(`/projects/${projectId}`);
      setDetail(data);
      setBudgetInput(data.project.totalBudget ? String(data.project.totalBudget) : '');
      await fetchContractFlowState();
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to load project details.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveBudget = async (e: FormEvent) => {
    e.preventDefault();
    const num = Number(budgetInput);
    if (!Number.isFinite(num) || num <= 0) {
      alert('Budget must be a positive number.');
      return;
    }
    setSavingBudget(true);
    try {
      await api.patch(`/projects/${projectId}`, { totalBudget: num });
      setEditingBudget(false);
      await fetchProjectDetail();
    } catch (err: unknown) {
      alert(err instanceof ApiError ? err.message : 'Failed to update project budget.');
    } finally {
      setSavingBudget(false);
    }
  };

  useEffect(() => {
    fetchProjectDetail();
  }, [projectId]);

  const handleSendInvite = async (e: FormEvent) => {
    e.preventDefault();
    setInviteError(null);
    setCopied(false);

    const email = inviteEmail.trim().toLowerCase();
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setInviteError('Please enter a valid email address.');
      return;
    }

    setInviting(true);
    try {
      const res = await api.post<InvitationResponse>(`/projects/${projectId}/invitations`, {
        email,
        message: inviteMessage.trim() || undefined,
      });

      setLatestInviteLink(res.invitationLink);
      setInviteEmail('');
      setInviteMessage('');
      // Refresh detail so activeInvitation updates
      fetchProjectDetail();
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to send invitation.';
      setInviteError(msg);
    } finally {
      setInviting(false);
    }
  };

  const handleCopyLink = (linkToCopy: string) => {
    navigator.clipboard.writeText(linkToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleCancelProject = async () => {
    if (!window.confirm('Are you sure you want to cancel this project? This will cancel all pending invitations.')) {
      return;
    }

    setCancelling(true);
    try {
      await api.post(`/projects/${projectId}/cancel`, {});
      fetchProjectDetail();
    } catch (err: unknown) {
      alert(err instanceof ApiError ? err.message : 'Failed to cancel project.');
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-12">
        <div className="flex items-center gap-3 text-slate-500 text-sm font-medium">
          <span className="w-5 h-5 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
          Loading workspace...
        </div>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="flex-1 max-w-2xl mx-auto px-4 py-16 text-center space-y-4">
        <div className="w-12 h-12 bg-red-50 text-red-600 rounded-full flex items-center justify-center mx-auto text-xl">
          ⚠️
        </div>
        <h2 className="text-lg font-bold text-slate-900">Unable to Open Workspace</h2>
        <p className="text-xs sm:text-sm text-slate-500">{error || 'Project not found.'}</p>
        <button
          type="button"
          onClick={() => navigate('/')}
          className="px-4 py-2 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition-colors"
        >
          &larr; Back to Dashboard
        </button>
      </div>
    );
  }

  const { project, currentUserRole, members, activeInvitation, milestones = [] } = detail;
  const isClient = currentUserRole === 'client';
  const milestonesEditable = ['draft', 'invitation_pending', 'awaiting_agreement'].includes(project.status);

  // Check if counterpart is unoccupied
  const isFreelancerOccupied = Boolean(project.freelancerId);
  const isClientOccupied = Boolean(project.clientId);
  const isCounterpartNeeded = (isClient && !isFreelancerOccupied) || (!isClient && !isClientOccupied);
  const counterpartRoleName = isClient ? 'Freelancer' : 'Client';

  return (
    <div className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Breadcrumb & Action */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => navigate('/')}
          className="text-xs text-slate-500 hover:text-slate-900 flex items-center gap-1 font-medium transition-colors"
        >
          &larr; Back to Dashboard
        </button>

        {project.status !== 'cancelled' && project.status !== 'completed' && (
          <button
            type="button"
            onClick={handleCancelProject}
            disabled={cancelling}
            className="text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50 px-3 py-1.5 rounded-lg border border-rose-200 transition-colors"
          >
            {cancelling ? 'Cancelling...' : 'Cancel Project'}
          </button>
        )}
      </div>

      {/* Project Header Banner */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-brand-50 text-brand-700 border border-brand-200 capitalize">
                {project.status.replace(/_/g, ' ')}
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
                You: {isClient ? '💼 Client' : '🛠️ Freelancer'}
              </span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                source v{project.sourceVersion ?? 1}
              </span>
              <span className="text-[11px] text-slate-400">
                Created on {new Date(project.createdAt).toLocaleDateString()}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900">{project.title}</h1>
            <p className="text-sm text-slate-600 leading-relaxed max-w-3xl">
              {project.description || 'No project description added.'}
            </p>
          </div>

          <div className="sm:text-right shrink-0 bg-slate-50 p-4 rounded-xl border border-slate-100 min-w-[180px] space-y-1">
            <span className="text-[10px] text-slate-400 font-bold block uppercase tracking-wider">
              Project Budget
            </span>
            {editingBudget ? (
              <form onSubmit={handleSaveBudget} className="space-y-1.5">
                <input
                  type="number"
                  min="1"
                  step="0.01"
                  required
                  value={budgetInput}
                  onChange={(e) => setBudgetInput(e.target.value)}
                  className="w-full px-2 py-1 border border-slate-300 rounded text-xs bg-white text-slate-900"
                />
                <div className="flex justify-end gap-1">
                  <button
                    type="button"
                    onClick={() => setEditingBudget(false)}
                    className="px-2 py-0.5 text-[11px] text-slate-600"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={savingBudget}
                    className="px-2 py-0.5 bg-brand-600 text-white rounded text-[11px] font-semibold"
                  >
                    Save
                  </button>
                </div>
              </form>
            ) : (
              <>
                <span className="text-xl font-bold text-slate-900">
                  {project.totalBudget
                    ? `${project.currency} ${Number(project.totalBudget).toLocaleString()}`
                    : 'Not set'}
                </span>
                <span className="text-[11px] text-slate-500 block capitalize">
                  {project.paymentArrangement?.replace(/_/g, ' ') || 'Milestone payment'}
                </span>
                {milestonesEditable && (
                  <button
                    type="button"
                    onClick={() => setEditingBudget(true)}
                    className="text-[11px] font-semibold text-brand-600 hover:underline block sm:ml-auto"
                  >
                    {project.totalBudget ? 'Update budget' : 'Set required budget'}
                  </button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Status Indicator */}
        {project.status === 'awaiting_agreement' && (
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl text-xs text-blue-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-base">🤝</span>
              <span>
                <strong>Both members connected!</strong> Next step: Configure planned milestones and approve the initial project agreement below.
              </span>
            </div>
            <span className="font-semibold text-blue-900 bg-blue-100 px-2 py-1 rounded">
              Agreement Stage
            </span>
          </div>
        )}

        {cfNotice && (
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800">
            ContractFlow microservice notice: {cfNotice}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Left 2 Cols: Members & Work Overview */}
        <div className="md:col-span-2 space-y-6">
          {/* Members Card */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900">Project Members ({members.length}/2)</h3>
            <div className="divide-y divide-slate-100">
              {members.map((m) => (
                <div key={m.id} className="py-3 flex items-center justify-between first:pt-0 last:pb-0">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-brand-100 text-brand-700 font-bold text-xs flex items-center justify-center border border-brand-200">
                      {m.profile.displayName.slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-900">{m.profile.displayName}</p>
                      <p className="text-[11px] text-slate-400">
                        Joined {new Date(m.joinedAt).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${
                      m.role === 'client'
                        ? 'bg-purple-50 text-purple-700 border-purple-200'
                        : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    }`}
                  >
                    {m.role === 'client' ? 'Client' : 'Freelancer'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Workflow Stage Preview */}
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-900">Project Lifecycle</h3>
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                <span className="block text-slate-400 text-[10px] uppercase font-bold">1. Connect</span>
                <span className="font-semibold text-slate-900">
                  {isCounterpartNeeded ? 'Inviting Talent' : 'Connected'}
                </span>
              </div>
              <div
                className={`p-3 rounded-xl border ${
                  project.status === 'awaiting_agreement'
                    ? 'bg-blue-50 border-blue-200 text-blue-900 font-bold'
                    : 'bg-slate-50 border-slate-200 text-slate-400'
                }`}
              >
                <span className="block text-[10px] uppercase font-bold">2. Agreement</span>
                <span>ContractFlow</span>
              </div>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-slate-400">
                <span className="block text-[10px] uppercase font-bold">3. Execution</span>
                <span>WorkBridge & Pay</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Col: Invitation or Status Card */}
        <div className="space-y-6">
          {isCounterpartNeeded ? (
            /* Invitation Action Card */
            <div className="bg-white border border-brand-200 rounded-2xl p-6 shadow-sm space-y-5">
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-900">
                  Invite {counterpartRoleName}
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Invite your collaborator to join this project workspace.
                </p>
              </div>

              {inviteError && (
                <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                  {inviteError}
                </div>
              )}

              {/* Active Pending Invitation Info */}
              {activeInvitation && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl space-y-2 text-xs">
                  <div className="flex items-center justify-between text-amber-900 font-semibold">
                    <span>Active Invitation</span>
                    <span className="text-[10px] uppercase bg-amber-100 px-1.5 py-0.5 rounded">Pending</span>
                  </div>
                  <p className="text-amber-700 text-[11px]">
                    Sent to: <strong>{activeInvitation.invitedEmail}</strong>
                  </p>
                  <p className="text-[10px] text-amber-600">
                    Expires on {new Date(activeInvitation.expiresAt).toLocaleDateString()}
                  </p>
                </div>
              )}

              {/* Generated Link Box */}
              {latestInviteLink && (
                <div className="p-3.5 bg-brand-50/50 border border-brand-200 rounded-xl space-y-2 text-xs">
                  <span className="font-semibold text-brand-900 text-xs block">
                    🔗 Usable Invitation Link
                  </span>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={latestInviteLink}
                      className="flex-1 px-2.5 py-1.5 bg-white border border-brand-200 rounded-lg text-xs text-slate-800 font-mono select-all focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={() => handleCopyLink(latestInviteLink)}
                      className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg font-semibold text-xs transition-colors shrink-0"
                    >
                      {copied ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                  <p className="text-[11px] text-brand-700 leading-normal">
                    Share this link directly with your collaborator. (Email delivery is pending outbound SMTP setup.)
                  </p>
                </div>
              )}

              {/* Send Invite Form */}
              {!activeInvitation && (
                <form onSubmit={handleSendInvite} className="space-y-3 pt-1">
                  <div className="space-y-1">
                    <label htmlFor="inviteEmail" className="block text-xs font-semibold text-slate-700">
                      Collaborator's Email *
                    </label>
                    <input
                      id="inviteEmail"
                      type="email"
                      required
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      placeholder="colleague@example.com"
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                    />
                  </div>

                  <div className="space-y-1">
                    <label htmlFor="inviteMessage" className="block text-xs font-semibold text-slate-700">
                      Personal Note (Optional)
                    </label>
                    <textarea
                      id="inviteMessage"
                      rows={2}
                      value={inviteMessage}
                      onChange={(e) => setInviteMessage(e.target.value)}
                      placeholder="e.g. Excited to work together on this!"
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={inviting}
                    className="w-full py-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2"
                  >
                    {inviting && (
                      <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    )}
                    Generate Invitation Link
                  </button>
                </form>
              )}
            </div>
          ) : (
            /* Both Members Occupied Card */
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-3 text-center">
              <div className="w-10 h-10 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center text-lg mx-auto">
                ✓
              </div>
              <h3 className="text-sm font-bold text-slate-900">Project Roster Full</h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                Both client and freelancer roles are filled. No additional invitations needed.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* WorkBridge Workspace Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          type="button"
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'overview'
              ? 'bg-slate-900 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          📄 Overview & Agreements
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('tasks')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'tasks'
              ? 'bg-slate-900 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          ☑ Tasks & Kanban
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('deliverables')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'deliverables'
              ? 'bg-slate-900 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          📦 Deliverables & Files
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('collaboration')}
          className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
            activeTab === 'collaboration'
              ? 'bg-slate-900 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          💬 Team Discussion
        </button>
      </div>

      {activeTab === 'tasks' && (
        <TasksView projectId={projectId} currentUserRole={currentUserRole} />
      )}

      {activeTab === 'deliverables' && (
        <DeliverablesView projectId={projectId} currentUserRole={currentUserRole} />
      )}

      {activeTab === 'collaboration' && (
        <CollaborationView projectId={projectId} />
      )}

      {activeTab === 'overview' && (
        <>
          {/* Planned Milestones & Deliverables */}
          <MilestonesPanel
            project={project}
            milestones={milestones}
            editable={milestonesEditable}
            onChanged={fetchProjectDetail}
          />

          {/* Initial Project Agreement Workflow */}
          <AgreementSection
            project={project}
            currentUserRole={currentUserRole}
            milestones={milestones}
            agreementBundle={agreementBundle}
            overview={cfOverview}
            loading={agreementLoading}
            onRefresh={fetchProjectDetail}
          />

          {/* ContractFlow Scope Assessments & Amendments (V3–V5) */}
          <AmendmentsSection
            project={project}
            currentUserRole={currentUserRole}
            currentAgreement={agreementBundle?.currentAgreement ?? null}
            overview={cfOverview}
            onRefresh={fetchProjectDetail}
          />
        </>
      )}
    </div>
  );
}
