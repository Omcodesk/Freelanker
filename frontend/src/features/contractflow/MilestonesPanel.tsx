import { useState, type FormEvent } from 'react';
import { ApiError } from '../../services/api.ts';
import { contractflowService } from '../../services/contractflowService.ts';
import type { Milestone, Project } from '../../types/index.ts';

interface MilestonesPanelProps {
  project: Project;
  milestones: Milestone[];
  editable: boolean;
  onChanged: () => void;
}

export function MilestonesPanel({ project, milestones, editable, onChanged }: MilestonesPanelProps) {
  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const resetForm = () => {
    setFormOpen(false);
    setEditingId(null);
    setTitle('');
    setDescription('');
    setAmount('');
    setDueDate('');
    setError(null);
  };

  const openCreate = () => {
    resetForm();
    setFormOpen(true);
  };

  const openEdit = (m: Milestone) => {
    setEditingId(m.id);
    setTitle(m.title);
    setDescription(m.description || '');
    setAmount(String(m.amount));
    setDueDate(m.dueDate || '');
    setError(null);
    setFormOpen(true);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const parsedAmount = Number(amount);
    if (!title.trim()) {
      setError('Milestone title is required.');
      return;
    }
    if (!Number.isFinite(parsedAmount) || parsedAmount < 0) {
      setError('Milestone amount must be a valid non-negative number.');
      return;
    }
    if (!dueDate) {
      setError('An explicit milestone due date is required.');
      return;
    }

    setSaving(true);
    try {
      if (editingId) {
        await contractflowService.updateMilestone(project.id, editingId, {
          title: title.trim(),
          description: description.trim() || undefined,
          amount: parsedAmount,
          dueDate,
        });
      } else {
        await contractflowService.createMilestone(project.id, {
          title: title.trim(),
          description: description.trim() || undefined,
          amount: parsedAmount,
          dueDate,
        });
      }
      resetForm();
      onChanged();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Failed to save milestone.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (milestoneId: string) => {
    if (!window.confirm('Remove this planned milestone?')) return;
    setDeletingId(milestoneId);
    setError(null);
    try {
      await contractflowService.deleteMilestone(project.id, milestoneId);
      onChanged();
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Failed to remove milestone.');
    } finally {
      setDeletingId(null);
    }
  };

  const allocatedTotal = milestones.reduce((sum, m) => sum + Number(m.amount || 0), 0);

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-bold text-slate-900">
            Planned Milestones & Deliverables ({milestones.length})
          </h3>
          <p className="text-xs text-slate-500">
            Explicit milestones and due dates anchor all ContractFlow agreements. Allocated:{' '}
            <strong className="text-slate-700">
              {project.currency} {allocatedTotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </strong>
            {project.totalBudget ? ` / ${project.currency} ${Number(project.totalBudget).toLocaleString()}` : ''}
          </p>
        </div>

        {editable && !formOpen && (
          <button
            type="button"
            onClick={openCreate}
            className="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold rounded-lg transition-colors shrink-0"
          >
            + Add Milestone
          </button>
        )}
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
          {error}
        </div>
      )}

      {formOpen && editable && (
        <form onSubmit={handleSubmit} className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-800">
              {editingId ? 'Edit Milestone' : 'New Planned Milestone'}
            </span>
            <button type="button" onClick={resetForm} className="text-xs text-slate-500 hover:text-slate-800">
              Cancel
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="sm:col-span-3 space-y-1">
              <label className="block text-[11px] font-semibold text-slate-700">Title *</label>
              <input
                type="text"
                required
                maxLength={200}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Architecture & Core API"
                className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-[11px] font-semibold text-slate-700">
                Amount ({project.currency}) *
              </label>
              <input
                type="number"
                required
                min="0"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-[11px] font-semibold text-slate-700">Due Date *</label>
              <input
                type="date"
                required
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            <div className="sm:col-span-3 space-y-1">
              <label className="block text-[11px] font-semibold text-slate-700">Deliverable Description</label>
              <textarea
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Concrete deliverable criteria for this milestone..."
                className="w-full px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={resetForm}
              disabled={saving}
              className="px-3 py-1.5 border border-slate-300 bg-white text-slate-700 text-xs font-semibold rounded-lg hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-1.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white text-xs font-semibold rounded-lg"
            >
              {saving ? 'Saving...' : editingId ? 'Save Changes' : 'Create Milestone'}
            </button>
          </div>
        </form>
      )}

      {milestones.length === 0 ? (
        <div className="p-5 bg-slate-50 border border-dashed border-slate-300 rounded-xl text-center space-y-1">
          <p className="text-xs font-semibold text-slate-700">No milestones defined yet</p>
          <p className="text-[11px] text-slate-500">
            Add at least one planned milestone with an explicit due date before submitting an agreement.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-slate-100">
          {milestones.map((m, idx) => (
            <div key={m.id} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 first:pt-0 last:pb-0">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                    #{idx + 1}
                  </span>
                  <span className="text-xs font-bold text-slate-900">{m.title}</span>
                </div>
                {m.description && <p className="text-xs text-slate-600">{m.description}</p>}
                <p className="text-[11px] text-slate-400">
                  Due: <strong className="text-slate-600">{m.dueDate || 'Missing due date'}</strong>
                </p>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <span className="text-xs font-bold text-slate-900">
                  {project.currency} {Number(m.amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                {editable && (
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => openEdit(m)}
                      className="px-2.5 py-1 text-[11px] font-semibold text-slate-700 border border-slate-200 rounded-lg hover:bg-slate-50"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => handleDelete(m.id)}
                      disabled={deletingId === m.id}
                      className="px-2.5 py-1 text-[11px] font-semibold text-rose-600 border border-rose-200 rounded-lg hover:bg-rose-50 disabled:opacity-50"
                    >
                      {deletingId === m.id ? '...' : 'Delete'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

