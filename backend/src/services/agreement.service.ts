import crypto from 'node:crypto';
import { supabaseAdmin } from '../lib/supabase.js';
import { logActivity } from './activity.service.js';
import { ProjectError } from './project.service.js';
import type { Agreement, AgreementApproval, PaymentArrangement } from '../types/index.js';

const ISO_DATE_REGEX = /^\d{4}-\d{2}-\d{2}$/;
const VALID_ARRANGEMENTS: PaymentArrangement[] = ['upfront', 'milestone_prepayment', 'payment_after_approval'];

export interface AgreementWithDigest extends Agreement {
  contentDigest: string;
}

export interface SaveAgreementDraftInput {
  title: string;
  scopeOfWork: string;
  deliverablesText?: string;
  acceptanceCriteria?: string;
  paymentArrangement: PaymentArrangement;
  totalAmount: number;
  currency?: string;
  revisionLimit?: number | null;
  reviewPeriodDays: number;
  startDate?: string | null;
  endDate?: string | null;
  additionalTerms?: string;
  isAiGenerated?: boolean;
  aiSummary?: string;
}

export interface AgreementDecisionInput {
  decision: 'APPROVE' | 'REJECT';
  expectedVersion: number;
  expectedDigest: string;
  notes?: string;
}

function canonicalize(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(canonicalize);
  }
  if (value !== null && typeof value === 'object') {
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(value as Record<string, unknown>).sort()) {
      out[key] = canonicalize((value as Record<string, unknown>)[key]);
    }
    return out;
  }
  return value;
}

export function computeAgreementDigest(row: any): string {
  const material = canonicalize({
    projectId: row.project_id,
    versionNumber: Number(row.version_number),
    title: row.title,
    scopeOfWork: row.scope_of_work ?? null,
    deliverablesText: row.deliverables_text ?? null,
    acceptanceCriteria: row.acceptance_criteria ?? null,
    paymentArrangement: row.payment_arrangement,
    totalAmount: Number(row.total_amount).toFixed(2),
    currency: String(row.currency || 'USD').trim().toUpperCase(),
    revisionLimit: row.revision_limit ?? null,
    reviewPeriodDays: Number(row.review_period_days),
    startDate: row.start_date ?? null,
    endDate: row.end_date ?? null,
    additionalTerms: row.additional_terms ?? null,
    contentSnapshot: row.content_snapshot ?? null,
  });
  return crypto.createHash('sha256').update(JSON.stringify(material), 'utf8').digest('hex');
}

function mapAgreementRow(row: any): AgreementWithDigest {
  return {
    id: row.id,
    projectId: row.project_id,
    versionNumber: Number(row.version_number),
    previousVersionId: row.previous_version_id || undefined,
    isCurrent: Boolean(row.is_current),
    status: row.status,
    title: row.title,
    scopeOfWork: row.scope_of_work || undefined,
    deliverablesText: row.deliverables_text || undefined,
    acceptanceCriteria: row.acceptance_criteria || undefined,
    paymentArrangement: row.payment_arrangement,
    totalAmount: Number(row.total_amount),
    currency: String(row.currency || 'USD').trim(),
    revisionLimit: row.revision_limit !== null && row.revision_limit !== undefined ? Number(row.revision_limit) : undefined,
    reviewPeriodDays: Number(row.review_period_days),
    startDate: row.start_date || undefined,
    endDate: row.end_date || undefined,
    additionalTerms: row.additional_terms || undefined,
    isAiGenerated: Boolean(row.is_ai_generated),
    pdfUrl: row.pdf_url || undefined,
    aiSummary: row.ai_summary || undefined,
    contentSnapshot: row.content_snapshot || undefined,
    clientApprovedAt: row.client_approved_at || undefined,
    freelancerApprovedAt: row.freelancer_approved_at || undefined,
    activatedAt: row.activated_at || undefined,
    supersededAt: row.superseded_at || undefined,
    createdBy: row.created_by,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    contentDigest: computeAgreementDigest(row),
  };
}

function mapApprovalRow(row: any): AgreementApproval {
  return {
    id: row.id,
    agreementId: row.agreement_id,
    userId: row.user_id,
    role: row.role,
    action: row.action,
    notes: row.notes || undefined,
    createdAt: row.created_at,
  };
}

function validateOptionalDate(value: unknown, fieldName: string): string | null {
  if (value === undefined || value === null || value === '') {
    return null;
  }
  if (typeof value !== 'string' || !ISO_DATE_REGEX.test(value.trim())) {
    throw new ProjectError(400, `${fieldName} must be a valid YYYY-MM-DD date.`);
  }
  const normalized = value.trim();
  const parsed = new Date(`${normalized}T00:00:00.000Z`);
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== normalized) {
    throw new ProjectError(400, `${fieldName} is not a valid calendar date.`);
  }
  return normalized;
}

async function buildAuthoritativeSnapshot(
  project: any,
  scopeText: string,
  totalAmount: number,
  currency: string
): Promise<Record<string, unknown> | null> {
  if (!project.client_id || !project.freelancer_id || project.client_id === project.freelancer_id) {
    return null;
  }

  const { data: profiles } = await supabaseAdmin
    .from('profiles')
    .select('id, display_name')
    .in('id', [project.client_id, project.freelancer_id]);

  const profileMap = new Map<string, string>((profiles || []).map((p: any) => [p.id, p.display_name || 'Member']));
  const { data: milestones } = await supabaseAdmin
    .from('milestones')
    .select('id, title, description, due_date, order_index')
    .eq('project_id', project.id)
    .order('order_index', { ascending: true })
    .order('created_at', { ascending: true });

  if (!milestones || milestones.length === 0 || milestones.some((m: any) => !m.due_date)) {
    return null;
  }

  const startDate = new Date(project.created_at).toISOString().slice(0, 10);
  const deadlines = milestones.map((m: any) => String(m.due_date));
  const maxDeadline = deadlines.reduce((max: string, d: string) => (d > max ? d : max), deadlines[0]);
  if (maxDeadline < startDate) {
    return null;
  }

  return {
    project_id: project.id,
    title: project.title,
    client: {
      id: project.client_id,
      name: profileMap.get(project.client_id) || 'Client',
    },
    freelancer: {
      id: project.freelancer_id,
      name: profileMap.get(project.freelancer_id) || 'Freelancer',
    },
    scope: scopeText,
    budget: totalAmount.toFixed(2),
    currency,
    start_date: startDate,
    deadline: maxDeadline,
    deliverables: milestones.map((m: any) => ({
      id: `deliv-${m.id}`,
      description: m.description || m.title,
      deadline: m.due_date,
    })),
    milestones: milestones.map((m: any) => ({
      id: m.id,
      description: m.description || m.title,
      deadline: m.due_date,
      deliverable_ids: [`deliv-${m.id}`],
    })),
  };
}

async function loadAgreementBundle(projectId: string) {
  const { data: rows, error: agErr } = await supabaseAdmin
    .from('agreements')
    .select('*')
    .eq('project_id', projectId)
    .order('version_number', { ascending: false });

  if (agErr) {
    throw new ProjectError(500, `Failed to load project agreements: ${agErr.message}`);
  }

  const versions = (rows || []).map(mapAgreementRow);
  const currentAgreement = versions.find((v) => v.isCurrent) ?? versions[0] ?? null;

  let approvals: AgreementApproval[] = [];
  if (versions.length > 0) {
    const { data: appRows, error: appErr } = await supabaseAdmin
      .from('agreement_approvals')
      .select('*')
      .in('agreement_id', versions.map((v) => v.id))
      .order('created_at', { ascending: true });

    if (appErr) {
      throw new ProjectError(500, `Failed to load agreement approvals: ${appErr.message}`);
    }
    approvals = (appRows || []).map(mapApprovalRow);
  }

  return { currentAgreement, versions, approvals };
}

export async function getProjectAgreements(projectId: string, userId: string) {
  const { data: member, error: memErr } = await supabaseAdmin
    .from('project_members')
    .select('role')
    .eq('project_id', projectId)
    .eq('user_id', userId)
    .maybeSingle();

  if (memErr) {
    throw new ProjectError(500, `Failed to verify membership: ${memErr.message}`);
  }
  if (!member) {
    throw new ProjectError(403, 'Access denied: You are not a member of this project.');
  }

  return loadAgreementBundle(projectId);
}

export async function saveAgreementDraft(
  projectId: string,
  userId: string,
  input: SaveAgreementDraftInput
) {
  const { data: member, error: memErr } = await supabaseAdmin
    .from('project_members')
    .select('role')
    .eq('project_id', projectId)
    .eq('user_id', userId)
    .maybeSingle();

  if (memErr) {
    throw new ProjectError(500, `Failed to verify membership: ${memErr.message}`);
  }
  if (!member) {
    throw new ProjectError(403, 'Access denied: You are not a member of this project.');
  }
  if (member.role !== 'client') {
    throw new ProjectError(403, 'Only the project client can author or edit the initial agreement draft.');
  }

  const { data: project, error: projErr } = await supabaseAdmin
    .from('projects')
    .select('*')
    .eq('id', projectId)
    .maybeSingle();

  if (projErr || !project) {
    throw new ProjectError(404, 'Project not found.');
  }
  if (!['draft', 'invitation_pending', 'awaiting_agreement'].includes(project.status)) {
    throw new ProjectError(400, `Agreement draft cannot be modified while project is '${project.status}'.`);
  }

  const title = input.title?.trim();
  const scopeOfWork = input.scopeOfWork?.trim();
  if (!title || title.length > 200) {
    throw new ProjectError(400, 'Agreement title is required (max 200 characters).');
  }
  if (!scopeOfWork || scopeOfWork.length > 8000) {
    throw new ProjectError(400, 'Scope of work is required.');
  }
  if (!VALID_ARRANGEMENTS.includes(input.paymentArrangement)) {
    throw new ProjectError(400, 'Invalid payment arrangement.');
  }
  if (typeof input.totalAmount !== 'number' || !Number.isFinite(input.totalAmount) || input.totalAmount <= 0) {
    throw new ProjectError(400, 'Agreement total amount must be greater than zero.');
  }
  const totalAmount = Math.round(input.totalAmount * 100) / 100;
  const currency = (input.currency?.trim() || project.currency || 'USD').toUpperCase().slice(0, 3);
  if (!/^[A-Z]{3}$/.test(currency)) {
    throw new ProjectError(400, 'Currency must be a 3-letter ISO code.');
  }
  if (!Number.isInteger(input.reviewPeriodDays) || input.reviewPeriodDays < 1) {
    throw new ProjectError(400, 'Review period days must be an integer >= 1.');
  }
  if (input.revisionLimit !== undefined && input.revisionLimit !== null) {
    if (!Number.isInteger(input.revisionLimit) || input.revisionLimit < 0) {
      throw new ProjectError(400, 'Revision limit must be a non-negative integer.');
    }
  }
  const startDate = validateOptionalDate(input.startDate, 'Start date');
  const endDate = validateOptionalDate(input.endDate, 'End date');
  if (startDate && endDate && startDate > endDate) {
    throw new ProjectError(400, 'Agreement start date must precede or equal end date.');
  }

  const { data: existingRows } = await supabaseAdmin
    .from('agreements')
    .select('*')
    .eq('project_id', projectId)
    .order('version_number', { ascending: false });

  const current = (existingRows || []).find((r: any) => r.is_current) ?? (existingRows || [])[0] ?? null;
  if (current && ['approved', 'active', 'completed'].includes(current.status)) {
    throw new ProjectError(409, 'Approved or active agreements are immutable. Use ContractFlow amendments for scope changes.');
  }

  const snapshot = await buildAuthoritativeSnapshot(project, scopeOfWork, totalAmount, currency);
  const payload = {
    title,
    scope_of_work: scopeOfWork,
    deliverables_text: input.deliverablesText?.trim() || null,
    acceptance_criteria: input.acceptanceCriteria?.trim() || null,
    payment_arrangement: input.paymentArrangement,
    total_amount: totalAmount,
    currency,
    revision_limit: input.revisionLimit ?? null,
    review_period_days: input.reviewPeriodDays,
    start_date: startDate,
    end_date: endDate,
    additional_terms: input.additionalTerms?.trim() || null,
    is_ai_generated: Boolean(input.isAiGenerated),
    ai_summary: input.aiSummary?.trim() || null,
    content_snapshot: snapshot,
    client_approved_at: null,
    freelancer_approved_at: null,
    updated_at: new Date().toISOString(),
  };

  let savedId: string;
  if (!current) {
    const { data: created, error: insErr } = await supabaseAdmin
      .from('agreements')
      .insert({
        project_id: projectId,
        version_number: 1,
        is_current: true,
        status: 'draft',
        created_by: userId,
        ...payload,
      })
      .select('*')
      .single();

    if (insErr || !created) {
      throw new ProjectError(500, `Failed to create agreement draft: ${insErr?.message}`);
    }
    savedId = created.id;
    await logActivity({
      projectId,
      actorId: userId,
      eventType: 'agreement_created',
      entityType: 'agreement',
      entityId: savedId,
      newData: { versionNumber: 1, title, totalAmount, currency },
    });
  } else if (current.status === 'draft' || current.status === 'changes_requested') {
    const { data: updated, error: updErr } = await supabaseAdmin
      .from('agreements')
      .update({
        status: 'draft',
        ...payload,
      })
      .eq('id', current.id)
      .select('*')
      .single();

    if (updErr || !updated) {
      throw new ProjectError(500, `Failed to update agreement draft: ${updErr?.message}`);
    }
    savedId = updated.id;
  } else {
    // Supersede sent_for_review agreement into a fresh revision so approvals never bind to edited content
    const nowIso = new Date().toISOString();
    const { error: supErr } = await supabaseAdmin
      .from('agreements')
      .update({
        is_current: false,
        status: 'cancelled',
        superseded_at: nowIso,
        updated_at: nowIso,
      })
      .eq('id', current.id);

    if (supErr) {
      throw new ProjectError(500, `Failed to supersede prior agreement revision: ${supErr.message}`);
    }

    const nextVer = Number(current.version_number) + 1;
    const { data: created, error: insErr } = await supabaseAdmin
      .from('agreements')
      .insert({
        project_id: projectId,
        version_number: nextVer,
        previous_version_id: current.id,
        is_current: true,
        status: 'draft',
        created_by: userId,
        ...payload,
      })
      .select('*')
      .single();

    if (insErr || !created) {
      throw new ProjectError(500, `Failed to create new agreement revision: ${insErr?.message}`);
    }
    savedId = created.id;
    await logActivity({
      projectId,
      actorId: userId,
      eventType: 'agreement_version_created',
      entityType: 'agreement',
      entityId: savedId,
      oldData: { versionNumber: current.version_number },
      newData: { versionNumber: nextVer, title, totalAmount, currency },
    });
  }

  return loadAgreementBundle(projectId);
}

export async function submitAgreementForReview(
  projectId: string,
  agreementId: string,
  userId: string,
  expectedVersion: number,
  expectedDigest: string
) {
  const { data: member, error: memErr } = await supabaseAdmin
    .from('project_members')
    .select('role')
    .eq('project_id', projectId)
    .eq('user_id', userId)
    .maybeSingle();

  if (memErr || !member) {
    throw new ProjectError(403, 'Access denied: You are not a member of this project.');
  }
  if (member.role !== 'client') {
    throw new ProjectError(403, 'Only the project client can submit an agreement revision for review.');
  }

  const { data: project } = await supabaseAdmin
    .from('projects')
    .select('*')
    .eq('id', projectId)
    .maybeSingle();

  if (!project) {
    throw new ProjectError(404, 'Project not found.');
  }
  if (!project.client_id || !project.freelancer_id || project.client_id === project.freelancer_id) {
    throw new ProjectError(409, 'Both client and freelancer must join the project before submitting an agreement for review.');
  }

  const { data: ag, error: agErr } = await supabaseAdmin
    .from('agreements')
    .select('*')
    .eq('id', agreementId)
    .eq('project_id', projectId)
    .maybeSingle();

  if (agErr || !ag) {
    throw new ProjectError(404, 'Agreement not found.');
  }
  if (!ag.is_current) {
    throw new ProjectError(409, 'Only the current agreement revision can be submitted for review.');
  }
  if (!['draft', 'changes_requested'].includes(ag.status)) {
    throw new ProjectError(409, `Agreement in '${ag.status}' state cannot be submitted for review.`);
  }
  if (Number(ag.version_number) !== expectedVersion || computeAgreementDigest(ag) !== expectedDigest) {
    throw new ProjectError(409, 'Agreement revision or digest does not match current saved draft. Refresh and retry.');
  }

  const snapshot = await buildAuthoritativeSnapshot(
    project,
    ag.scope_of_work || project.description || project.title,
    Number(ag.total_amount),
    String(ag.currency || project.currency || 'USD').trim().toUpperCase()
  );
  if (!snapshot) {
    throw new ProjectError(409, 'At least one milestone with an explicit due date is required before submitting the agreement for review.');
  }

  const { error: updErr } = await supabaseAdmin
    .from('agreements')
    .update({
      status: 'sent_for_review',
      content_snapshot: snapshot,
      client_approved_at: null,
      freelancer_approved_at: null,
      updated_at: new Date().toISOString(),
    })
    .eq('id', agreementId)
    .eq('project_id', projectId);

  if (updErr) {
    throw new ProjectError(500, `Failed to submit agreement for review: ${updErr.message}`);
  }

  return loadAgreementBundle(projectId);
}

export async function decideAgreement(
  projectId: string,
  agreementId: string,
  userId: string,
  input: AgreementDecisionInput
) {
  const { data: member, error: memErr } = await supabaseAdmin
    .from('project_members')
    .select('role')
    .eq('project_id', projectId)
    .eq('user_id', userId)
    .maybeSingle();

  if (memErr || !member) {
    throw new ProjectError(403, 'Access denied: You are not a member of this project.');
  }
  if (input.decision !== 'APPROVE' && input.decision !== 'REJECT') {
    throw new ProjectError(422, "Decision must be 'APPROVE' or 'REJECT'.");
  }
  if (!Number.isInteger(input.expectedVersion) || input.expectedVersion < 1 || !/^[0-9a-f]{64}$/i.test(input.expectedDigest || '')) {
    throw new ProjectError(422, 'Valid expectedVersion and 64-character hex expectedDigest are required.');
  }
  if (input.decision === 'REJECT' && (!input.notes || !input.notes.trim())) {
    throw new ProjectError(422, 'Feedback notes are required when requesting changes / rejecting.');
  }

  const { data: ag, error: agErr } = await supabaseAdmin
    .from('agreements')
    .select('*')
    .eq('id', agreementId)
    .eq('project_id', projectId)
    .maybeSingle();

  if (agErr || !ag) {
    throw new ProjectError(404, 'Agreement not found.');
  }
  if (!ag.is_current) {
    throw new ProjectError(409, 'This agreement revision has been superseded.');
  }
  if (ag.status !== 'sent_for_review') {
    throw new ProjectError(409, `Agreement cannot be decided while in '${ag.status}' state.`);
  }
  if (Number(ag.version_number) !== input.expectedVersion || computeAgreementDigest(ag) !== input.expectedDigest) {
    throw new ProjectError(409, 'Agreement content or version changed before your decision. Refresh and review again.');
  }

  const role: 'client' | 'freelancer' = member.role;
  const alreadyApprovedByRole =
    (role === 'client' && Boolean(ag.client_approved_at)) ||
    (role === 'freelancer' && Boolean(ag.freelancer_approved_at));
  if (alreadyApprovedByRole) {
    throw new ProjectError(409, `The ${role} has already recorded an approval for this revision.`);
  }

  const nowIso = new Date().toISOString();
  const action = input.decision === 'APPROVE' ? 'approved' : 'changes_requested';

  const { error: appInsErr } = await supabaseAdmin.from('agreement_approvals').insert({
    agreement_id: agreementId,
    user_id: userId,
    role,
    action,
    notes: input.notes?.trim() || null,
    created_at: nowIso,
  });

  if (appInsErr) {
    throw new ProjectError(500, `Failed to record agreement approval decision: ${appInsErr.message}`);
  }

  if (input.decision === 'REJECT') {
    const { error: rejErr } = await supabaseAdmin
      .from('agreements')
      .update({
        status: 'changes_requested',
        client_approved_at: null,
        freelancer_approved_at: null,
        updated_at: nowIso,
      })
      .eq('id', agreementId);

    if (rejErr) {
      throw new ProjectError(500, `Failed to update agreement status: ${rejErr.message}`);
    }
  } else {
    const nextClientApproved = role === 'client' ? nowIso : ag.client_approved_at;
    const nextFreelancerApproved = role === 'freelancer' ? nowIso : ag.freelancer_approved_at;
    const bothApproved = Boolean(nextClientApproved && nextFreelancerApproved);

    const agUpdate: Record<string, unknown> = {
      client_approved_at: nextClientApproved,
      freelancer_approved_at: nextFreelancerApproved,
      updated_at: nowIso,
    };
    if (bothApproved) {
      agUpdate.status = 'active';
      agUpdate.activated_at = nowIso;
    }

    const { error: updErr } = await supabaseAdmin
      .from('agreements')
      .update(agUpdate)
      .eq('id', agreementId);

    if (updErr) {
      throw new ProjectError(500, `Failed to update agreement approval timestamps: ${updErr.message}`);
    }

    await logActivity({
      projectId,
      actorId: userId,
      eventType: 'agreement_approved',
      entityType: 'agreement',
      entityId: agreementId,
      newData: { role, versionNumber: ag.version_number, contentDigest: input.expectedDigest, bothApproved },
    });

    if (bothApproved) {
      await supabaseAdmin
        .from('projects')
        .update({ status: 'active', updated_at: nowIso })
        .eq('id', projectId)
        .in('status', ['draft', 'invitation_pending', 'awaiting_agreement']);

      await logActivity({
        projectId,
        actorId: userId,
        eventType: 'agreement_activated',
        entityType: 'agreement',
        entityId: agreementId,
        newData: { versionNumber: ag.version_number, contentDigest: input.expectedDigest },
      });
    }
  }

  return loadAgreementBundle(projectId);
}

