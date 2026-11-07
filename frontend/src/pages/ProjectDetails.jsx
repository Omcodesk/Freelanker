import { useEffect, useState } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import { ArrowLeft as ArrowLeftIcon, Check, CheckSquare, Diamond, MessageSquare, PartyPopper, RotateCcw, Upload, X } from "lucide-react";
import { api } from "../api";
import Progress from "../components/Progress";
import Modal from "../components/Modal";

export default function ProjectDetails({ toast }) {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [showMember, setShowMember] = useState(false);
  const [member, setMember] = useState({ name: "", role: "member" });
  const { refresh } = useOutletContext();

  const load = () => api.get(`/api/projects/${id}`).then(setP).catch(() => {});
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (!p) return <div className="empty">Loadingâ€¦</div>;

  const addMember = async () => {
    if (!member.name.trim()) return;
    await api.post(`/api/projects/${p.id}/members`, member);
    setShowMember(false);
    setMember({ name: "", role: "member" });
    load();
    toast("Member added");
  };

  const removeMember = async (mid) => {
    await api.del(`/api/projects/${p.id}/members/${mid}`);
    load();
  };

  const setStatus = async (status) => {
    await api.put(`/api/projects/${p.id}`, { status });
    load();
    toast(`Project marked ${status}`);
  };

  const upcoming = p.milestones.filter((m) => m.status !== "approved");

  return (
    <div>
      <Link to="/" className="back-link"><ArrowLeftIcon /> All projects</Link>

      <div className="section-head">
        <div>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <h2 style={{ fontSize: 22 }}>{p.name}</h2>
            <span className={`badge ${p.status}`}>{p.status}</span>
          </div>
          <div className="page-sub">
            Contract <b style={{ color: "var(--accent)" }}>{p.contract_ref || "â€”"}</b> Â· created{" "}
            {p.created_at ? new Date(p.created_at).toLocaleDateString() : ""}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {p.status !== "completed" && (
            <button className="btn ghost sm" onClick={() => setStatus("completed")}>
              <Check size={13} style={{ display: "inline", verticalAlign: "-2px" }} /> Mark completed
            </button>
          )}
          {p.status === "completed" && (
            <button className="btn ghost sm" onClick={() => setStatus("active")}>
              â†© Reopen
            </button>
          )}
        </div>
      </div>

      <div className="stats">
        <div className="stat">
          <div className="v">{p.progress}%</div>
          <div className="l">Overall progress</div>
        </div>
        <div className="stat">
          <div className="v">
            {p.tasks_done}/{p.tasks_total}
          </div>
          <div className="l">Tasks done</div>
        </div>
        <div className="stat">
          <div className="v">
            {p.milestones_approved}/{p.milestones_total}
          </div>
          <div className="l">Milestones approved</div>
        </div>
        <div className="stat">
          <div className="v">â‚¹{(p.budget || 0).toLocaleString("en-IN")}</div>
          <div className="l">Budget</div>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1.4fr 1fr", gap: 16 }}>
        <div className="card">
          <h3>About</h3>
          <p className="meta" style={{ marginTop: 8, fontSize: 14 }}>
            {p.description || "No description."}
          </p>
          <div style={{ marginTop: 18 }}>
            <Progress value={p.progress} done={p.tasks_done} total={p.tasks_total} />
          </div>
          <div style={{ marginTop: 18 }}>
            <b style={{ fontSize: 13 }}>Next milestones</b>
            {upcoming.length === 0 && (
              <div className="meta" style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 6 }}>
                <PartyPopper size={14} /> All milestones approved
              </div>
            )}
            {upcoming.map((m) => (
              <div key={m.id} style={{ display: "flex", justifyContent: "space-between", marginTop: 10, fontSize: 13.5 }}>
                <span>
                  {m.title} <span className={`badge ${m.status}`} style={{ marginLeft: 6 }}>{m.status}</span>
                </span>
                <span style={{ color: "var(--muted)" }}>{m.due_date || "â€”"}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>Team</h3>
            <button className="btn ghost sm" onClick={() => setShowMember(true)}>+ Add</button>
          </div>
          <div style={{ marginTop: 12 }}>
            {p.members.map((m) => (
              <div key={m.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "9px 0", borderBottom: "1px solid var(--border)" }}>
                <div className="avatar" style={{ width: 32, height: 32, fontSize: 13 }}>{m.name[0]?.toUpperCase()}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{m.name}</div>
                  <div style={{ fontSize: 11.5, color: "var(--accent)" }}>{m.role}</div>
                </div>
                <button className="btn danger sm" onClick={() => removeMember(m.id)}>
                  <X size={13} />
                </button>
              </div>
            ))}
            {p.members.length === 0 && <div className="empty" style={{ padding: 20 }}>No members</div>}
          </div>
        </div>
      </div>

      <div className="grid cols-3" style={{ marginTop: 16 }}>
        <Link to={`/projects/${p.id}/tasks`} className="card">
          <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <CheckSquare size={16} /> Task Management
          </h3>
          <div className="meta">Kanban board Â· assign Â· due dates Â· {p.tasks_total} tasks</div>
        </Link>
        <Link to={`/projects/${p.id}/milestones`} className="card">
          <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Diamond size={16} /> Milestone Tracking
          </h3>
          <div className="meta">Progress Â· approval â†’ PayPal payout hook</div>
        </Link>
        <Link to={`/projects/${p.id}/collaboration`} className="card">
          <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <MessageSquare size={16} /> Collaboration
          </h3>
          <div className="meta">Comments & updates between client and freelancer</div>
        </Link>
        <Link to={`/projects/${p.id}/deliverables`} className="card">
          <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Upload size={16} /> Deliverables
          </h3>
          <div className="meta">Upload Â· review Â· approve / request revision</div>
        </Link>
      </div>

      {showMember && (
        <Modal title="Add team member" onClose={() => setShowMember(false)}>
          <div className="field">
            <label>Name *</label>
            <input value={member.name} onChange={(e) => setMember({ ...member, name: e.target.value })} autoFocus />
          </div>
          <div className="field">
            <label>Role</label>
            <select value={member.role} onChange={(e) => setMember({ ...member, role: e.target.value })}>
              <option value="member">Member</option>
              <option value="client">Client</option>
              <option value="freelancer">Freelancer</option>
            </select>
          </div>
          <div className="modal-actions">
            <button className="btn ghost" onClick={() => setShowMember(false)}>Cancel</button>
            <button className="btn" onClick={addMember}>Add member</button>
          </div>
        </Modal>
      )}
    </div>
  );
}
