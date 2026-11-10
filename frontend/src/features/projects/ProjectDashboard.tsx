import { useEffect, useState } from 'react';
import { api, ApiError } from '../../services/api.ts';
import { useRouter } from '../../lib/router.tsx';
import { useAuth } from '../auth/AuthContext.tsx';
import { CreateProjectModal } from './CreateProjectModal.tsx';
import type { Project, ProjectStatus } from '../../types/index.ts';

type UserProject = Project & { currentUserRole: 'client' | 'freelancer' };

export function ProjectDashboard() {
  const { user } = useAuth();
  const { navigate } = useRouter();

  const [projects, setProjects] = useState<UserProject[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const fetchProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<{ projects: UserProject[] }>('/projects');
      setProjects(response.projects || []);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to load projects.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      fetchProjects();
    }
  }, [user]);

  const filteredProjects = projects.filter((p) => {
    if (statusFilter === 'all') return true;
    return p.status === statusFilter;
  });

  const getStatusBadge = (status: ProjectStatus) => {
    switch (status) {
      case 'draft':
        return {
          label: 'Draft',
          className: 'bg-slate-100 text-slate-700 border-slate-200',
        };
      case 'invitation_pending':
        return {
          label: 'Invitation Pending',
          className: 'bg-amber-50 text-amber-700 border-amber-200',
        };
      case 'awaiting_agreement':
        return {
          label: 'Awaiting Agreement',
          className: 'bg-blue-50 text-blue-700 border-blue-200',
        };
      case 'active':
      case 'in_progress':
        return {
          label: 'Active',
          className: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        };
      case 'completed':
        return {
          label: 'Completed',
          className: 'bg-green-50 text-green-700 border-green-200',
        };
      case 'cancelled':
        return {
          label: 'Cancelled',
          className: 'bg-rose-50 text-rose-700 border-rose-200',
        };
      case 'disputed':
        return {
          label: 'Disputed',
          className: 'bg-purple-50 text-purple-700 border-purple-200',
        };
      default:
        return {
          label: status,
          className: 'bg-slate-100 text-slate-700 border-slate-200',
        };
    }
  };

  return (
    <div className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner / Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Project Workspace</h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Manage your collaborations, invite talent or clients, and track project agreements.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setCreateModalOpen(true)}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs sm:text-sm font-semibold rounded-xl shadow-sm transition-colors shrink-0"
        >
          <span className="text-base leading-none">＋</span> Create Project
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between gap-2 overflow-x-auto pb-2">
        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl text-xs font-medium">
          {['all', 'draft', 'invitation_pending', 'awaiting_agreement', 'active', 'completed'].map(
            (tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setStatusFilter(tab)}
                className={`px-3 py-1.5 rounded-lg capitalize transition-colors ${
                  statusFilter === tab
                    ? 'bg-white text-slate-900 shadow-sm font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {tab === 'all'
                  ? 'All Projects'
                  : tab === 'invitation_pending'
                  ? 'Invites'
                  : tab.replace('_', ' ')}
              </button>
            )
          )}
        </div>
        <button
          type="button"
          onClick={fetchProjects}
          className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1 rounded transition-colors flex items-center gap-1"
        >
          <span>↻</span> Refresh
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-center justify-between">
          <span>{error}</span>
          <button
            type="button"
            onClick={fetchProjects}
            className="underline font-semibold hover:text-red-800"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4 animate-pulse shadow-sm"
            >
              <div className="h-4 bg-slate-200 rounded w-3/4" />
              <div className="h-3 bg-slate-100 rounded w-1/2" />
              <div className="h-16 bg-slate-50 rounded" />
              <div className="flex justify-between items-center pt-2">
                <div className="h-5 bg-slate-200 rounded w-20" />
                <div className="h-8 bg-slate-200 rounded w-24" />
              </div>
            </div>
          ))}
        </div>
      ) : filteredProjects.length === 0 ? (
        /* Empty State */
        <div className="bg-white border border-dashed border-slate-300 rounded-2xl p-12 text-center max-w-lg mx-auto space-y-4 shadow-sm">
          <div className="w-14 h-14 bg-brand-50 text-brand-600 rounded-2xl flex items-center justify-center text-2xl mx-auto shadow-inner">
            📂
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-slate-900">
              {statusFilter === 'all' ? 'No projects yet' : `No ${statusFilter.replace('_', ' ')} projects`}
            </h3>
            <p className="text-xs text-slate-500 max-w-xs mx-auto leading-relaxed">
              Create a project to initiate agreements, invite collaborators, and start tracking deliverables.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setCreateModalOpen(true)}
            className="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold rounded-xl shadow-sm transition-colors"
          >
            Create Your First Project
          </button>
        </div>
      ) : (
        /* Projects Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredProjects.map((project) => {
            const badge = getStatusBadge(project.status);
            const isClient = project.currentUserRole === 'client';

            return (
              <div
                key={project.id}
                onClick={() => navigate(`/projects/${project.id}`)}
                className="bg-white border border-slate-200 hover:border-brand-300 hover:shadow-md rounded-2xl p-6 flex flex-col justify-between transition-all cursor-pointer group"
              >
                <div className="space-y-3">
                  {/* Badges */}
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${badge.className}`}
                    >
                      {badge.label}
                    </span>
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${
                        isClient
                          ? 'bg-purple-50 text-purple-700 border border-purple-200'
                          : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      }`}
                    >
                      {isClient ? '💼 Client' : '🛠️ Freelancer'}
                    </span>
                  </div>

                  {/* Title & Description */}
                  <div>
                    <h3 className="text-base font-bold text-slate-900 group-hover:text-brand-600 transition-colors line-clamp-1">
                      {project.title}
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                      {project.description || 'No description provided.'}
                    </p>
                  </div>
                </div>

                {/* Footer Details */}
                <div className="pt-5 mt-5 border-t border-slate-100 flex items-center justify-between text-xs">
                  <div>
                    <span className="text-[10px] text-slate-400 block font-medium">BUDGET</span>
                    <span className="font-bold text-slate-900">
                      {project.totalBudget
                        ? `${project.currency} ${Number(project.totalBudget).toLocaleString()}`
                        : 'Flexible'}
                    </span>
                  </div>

                  <span className="text-brand-600 font-semibold text-xs flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                    Workspace &rarr;
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Creation Modal */}
      <CreateProjectModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onProjectCreated={(newProject) => {
          navigate(`/projects/${newProject.id}`);
        }}
      />
    </div>
  );
}
