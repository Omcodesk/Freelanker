import { useEffect, useState } from 'react';
import { api, ApiError } from '../../services/api.ts';

export interface TaskItem {
  id: string;
  projectId: string;
  milestoneId: string | null;
  title: string;
  description: string | null;
  status: 'todo' | 'in_progress' | 'done';
  assignedTo: string | null;
  dueDate: string | null;
  orderIndex: number;
  assignedProfile?: {
    id: string;
    displayName: string;
    avatarUrl: string | null;
  } | null;
}

interface TasksViewProps {
  projectId: string;
  currentUserRole?: 'client' | 'freelancer' | 'member';
}

const COLUMNS: { key: 'todo' | 'in_progress' | 'done'; label: string; badgeColor: string }[] = [
  { key: 'todo', label: 'To Do', badgeColor: 'bg-slate-100 text-slate-700' },
  { key: 'in_progress', label: 'In Progress', badgeColor: 'bg-amber-100 text-amber-800' },
  { key: 'done', label: 'Done', badgeColor: 'bg-emerald-100 text-emerald-800' },
];

export function TasksView({ projectId }: TasksViewProps) {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New task form state
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newDueDate, setNewDueDate] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadTasks = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get<TaskItem[]>(`/workbridge/projects/${projectId}/tasks`);
      setTasks(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load tasks.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, [projectId]);

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setSubmitting(true);
    try {
      const created = await api.post<TaskItem>(`/workbridge/projects/${projectId}/tasks`, {
        title: newTitle.trim(),
        description: newDesc.trim() || undefined,
        dueDate: newDueDate || undefined,
        status: 'todo',
      });
      setTasks((prev) => [...prev, created]);
      setNewTitle('');
      setNewDesc('');
      setNewDueDate('');
      setShowAddModal(false);
    } catch (err) {
      alert(err instanceof ApiError ? err.message : 'Failed to create task.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleMoveStatus = async (task: TaskItem, newStatus: 'todo' | 'in_progress' | 'done') => {
    try {
      const updated = await api.patch<TaskItem>(
        `/workbridge/projects/${projectId}/tasks/${task.id}`,
        { status: newStatus }
      );
      setTasks((prev) => prev.map((t) => (t.id === task.id ? updated : t)));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : 'Failed to update task.');
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!window.confirm('Delete this task?')) return;
    try {
      await api.delete(`/workbridge/projects/${projectId}/tasks/${taskId}`);
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
    } catch (err) {
      alert(err instanceof ApiError ? err.message : 'Failed to delete task.');
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-500 text-sm flex items-center justify-center gap-2">
        <span className="w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
        Loading tasks...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-slate-900">Task Management</h3>
          <p className="text-xs text-slate-500">
            {tasks.filter((t) => t.status === 'done').length} of {tasks.length} tasks completed
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowAddModal(true)}
          className="px-3.5 py-2 bg-brand-600 hover:bg-brand-700 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors flex items-center gap-1.5"
        >
          + Add Task
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Kanban Board */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {COLUMNS.map((col) => {
          const colTasks = tasks.filter((t) => t.status === col.key);
          return (
            <div key={col.key} className="bg-slate-50/80 border border-slate-200 rounded-2xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800">{col.label}</span>
                <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${col.badgeColor}`}>
                  {colTasks.length}
                </span>
              </div>

              {colTasks.length === 0 ? (
                <div className="p-6 text-center text-slate-400 text-xs border border-dashed border-slate-200 rounded-xl">
                  No tasks
                </div>
              ) : (
                <div className="space-y-2.5">
                  {colTasks.map((task) => (
                    <div
                      key={task.id}
                      className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-sm space-y-2 hover:border-slate-300 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <h4 className="text-xs font-bold text-slate-900">{task.title}</h4>
                        <button
                          type="button"
                          onClick={() => handleDeleteTask(task.id)}
                          className="text-slate-400 hover:text-red-600 text-xs"
                          title="Delete task"
                        >
                          ✕
                        </button>
                      </div>

                      {task.description && (
                        <p className="text-[11px] text-slate-600 line-clamp-2 leading-relaxed">
                          {task.description}
                        </p>
                      )}

                      <div className="flex items-center justify-between pt-1 text-[10px] text-slate-400">
                        {task.dueDate ? <span>📅 {task.dueDate}</span> : <span>No date</span>}
                        {task.assignedProfile && (
                          <span className="font-semibold text-slate-600">
                            👤 {task.assignedProfile.displayName}
                          </span>
                        )}
                      </div>

                      {/* Move controls */}
                      <div className="pt-2 border-t border-slate-100 flex items-center justify-end gap-1.5">
                        {col.key !== 'todo' && (
                          <button
                            type="button"
                            onClick={() =>
                              handleMoveStatus(task, col.key === 'done' ? 'in_progress' : 'todo')
                            }
                            className="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-[10px] font-semibold rounded-lg transition-colors"
                          >
                            ← Back
                          </button>
                        )}
                        {col.key !== 'done' && (
                          <button
                            type="button"
                            onClick={() =>
                              handleMoveStatus(task, col.key === 'todo' ? 'in_progress' : 'done')
                            }
                            className="px-2 py-1 bg-brand-50 hover:bg-brand-100 text-brand-700 text-[10px] font-semibold rounded-lg transition-colors"
                          >
                            {col.key === 'todo' ? 'Start →' : 'Done ✓'}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Add Task Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 max-w-md w-full shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-900">Add Task</h3>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateTask} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Title *</label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Design navigation flow"
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Description</label>
                <textarea
                  rows={2}
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Optional details or context"
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Due Date</label>
                <input
                  type="date"
                  value={newDueDate}
                  onChange={(e) => setNewDueDate(e.target.value)}
                  className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || !newTitle.trim()}
                  className="px-4 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-semibold disabled:opacity-50"
                >
                  {submitting ? 'Creating...' : 'Create Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
