import { useState, type FormEvent } from 'react';
import { api, ApiError } from '../../services/api.ts';
import type { Project, PaymentArrangement } from '../../types/index.ts';

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated: (project: Project) => void;
}

export function CreateProjectModal({
  isOpen,
  onClose,
  onProjectCreated,
}: CreateProjectModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [role, setRole] = useState<'client' | 'freelancer'>('client');
  const [currency, setCurrency] = useState('USD');
  const [totalBudget, setTotalBudget] = useState<string>('');
  const [paymentArrangement, setPaymentArrangement] =
    useState<PaymentArrangement>('milestone_prepayment');
  const [reviewPeriodDays, setReviewPeriodDays] = useState<number>(3);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setFormError('Please provide a project title.');
      return;
    }

    if (trimmedTitle.length > 200) {
      setFormError('Project title cannot exceed 200 characters.');
      return;
    }

    let parsedBudget: number | undefined = undefined;
    if (totalBudget.trim()) {
      const num = Number(totalBudget);
      if (isNaN(num) || num <= 0) {
        setFormError('Total budget must be a positive number.');
        return;
      }
      parsedBudget = num;
    }

    if (reviewPeriodDays < 1) {
      setFormError('Review period must be at least 1 day.');
      return;
    }

    setSubmitting(true);

    try {
      const response = await api.post<{ project: Project; membership: unknown }>(
        '/projects',
        {
          title: trimmedTitle,
          description: description.trim() || undefined,
          role,
          currency,
          totalBudget: parsedBudget,
          paymentArrangement,
          reviewPeriodDays,
        }
      );

      onProjectCreated(response.project);
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof ApiError ? err.message : 'Failed to create project. Please try again.';
      setFormError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-lg p-6 sm:p-8 space-y-6 animate-in fade-in zoom-in-95 duration-150 my-8">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Create New Project</h2>
            <p className="text-xs text-slate-500">
              Start a project as a hiring client or service-providing freelancer.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 rounded-lg p-1 transition-colors text-lg"
          >
            ✕
          </button>
        </div>

        {formError && (
          <div className="p-3 text-xs bg-red-50 border border-red-200 text-red-700 rounded-lg">
            {formError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Role Selection */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-700">
              Your Role in this Project
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setRole('client')}
                className={`py-2.5 px-3 rounded-xl border text-xs font-medium text-left transition-all ${
                  role === 'client'
                    ? 'border-brand-600 bg-brand-50/50 text-brand-900 ring-2 ring-brand-500/20'
                    : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                }`}
              >
                <div className="font-semibold text-slate-900">💼 Client (Hiring)</div>
                <div className="text-[11px] text-slate-500">I want to hire a freelancer</div>
              </button>
              <button
                type="button"
                onClick={() => setRole('freelancer')}
                className={`py-2.5 px-3 rounded-xl border text-xs font-medium text-left transition-all ${
                  role === 'freelancer'
                    ? 'border-brand-600 bg-brand-50/50 text-brand-900 ring-2 ring-brand-500/20'
                    : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                }`}
              >
                <div className="font-semibold text-slate-900">🛠️ Freelancer (Talent)</div>
                <div className="text-[11px] text-slate-500">I am delivering the work</div>
              </button>
            </div>
          </div>

          {/* Title */}
          <div className="space-y-1.5">
            <label htmlFor="title" className="block text-xs font-semibold text-slate-700">
              Project Title *
            </label>
            <input
              id="title"
              type="text"
              required
              maxLength={200}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Mobile Banking App Redesign"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
            />
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <label htmlFor="description" className="block text-xs font-semibold text-slate-700">
              Description (Optional)
            </label>
            <textarea
              id="description"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Briefly describe the project scope and expected outcomes..."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
            />
          </div>

          {/* Budget & Currency */}
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2 space-y-1.5">
              <label htmlFor="budget" className="block text-xs font-semibold text-slate-700">
                Budget (Optional)
              </label>
              <input
                id="budget"
                type="number"
                min="1"
                step="0.01"
                value={totalBudget}
                onChange={(e) => setTotalBudget(e.target.value)}
                placeholder="5000"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="currency" className="block text-xs font-semibold text-slate-700">
                Currency
              </label>
              <select
                id="currency"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
              </select>
            </div>
          </div>

          {/* Payment Arrangement */}
          <div className="space-y-1.5">
            <label htmlFor="arrangement" className="block text-xs font-semibold text-slate-700">
              Payment Arrangement
            </label>
            <select
              id="arrangement"
              value={paymentArrangement}
              onChange={(e) => setPaymentArrangement(e.target.value as PaymentArrangement)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
            >
              <option value="milestone_prepayment">Milestone Prepayment (Recommended)</option>
              <option value="payment_after_approval">Payment After Approval</option>
              <option value="upfront">Full Upfront Payment</option>
            </select>
          </div>

          {/* Review Period */}
          <div className="space-y-1.5">
            <label htmlFor="reviewPeriod" className="block text-xs font-semibold text-slate-700">
              Client Review Period (Days)
            </label>
            <input
              id="reviewPeriod"
              type="number"
              min="1"
              max="30"
              value={reviewPeriodDays}
              onChange={(e) => setReviewPeriodDays(parseInt(e.target.value, 10) || 3)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
            />
            <p className="text-[11px] text-slate-400">
              Standard review window for deliverables before automated acceptance triggers.
            </p>
          </div>

          {/* Submit button */}
          <div className="pt-2 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="px-4 py-2 border border-slate-200 text-slate-700 text-xs font-semibold rounded-lg hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors flex items-center gap-2"
            >
              {submitting && (
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              )}
              Create Project
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
