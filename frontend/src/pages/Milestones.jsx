import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft as ArrowLeftIcon, Check, Play as PlayIcon, X } from "lucide-react";
import { api } from "../api";
import Modal from "../components/Modal";

export default function Milestones({ toast }) {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", due_date: "", amount: "" });

  const load = () => api.get(`/api/projects/${id}`).then(setP).catch(() => {});
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (!p) return <div className="empty">Loadingâ€¦</div>;

  const create = async () => {
    if (!form.title.trim()) return;
    await api.post(`/api/projects/${p.id}/milestones`, { ...form, amount: Number(form.amount) || 0 });
    setShow(false);
    setForm({ title: "", description: "", due_date: "", amount: "" });
    load();
    toast("Milestone added");
  };

  const setStatus = async (m, status) => {
    await api.put(`/api/milestones/${m.id}`, { status });
    load();
    toast(status === "approved" ? `"${m.title}" approved â€” Person 1 can now pay via PayPal` : `Status â†’ ${status}`);
  };

  const remove = async (m) => {
    await api.del(`/api/milestones/${m.id}`);
    load();
    toast("Milestone deleted");
  };

  const approvedAmount = p.milestones.filter((m) => m.status === "approved").reduce((s, m) => s + m.amount, 0);

  return (
    <div>
      <Link to={`/projects/${p.id}`} className="back-link"><ArrowLeftIcon /> {p.name}</Link>
      <div className="section-head">
        <div>
          <h2 style={{ fontSize: 20 }}>Milestone Tracking</h2>
          <div className="page-sub">
            {p.milestones_approved}/{p.milestones_total} approved Â· â‚¹{approvedAmount.toLocaleString("en-IN")} released for payout
          </div>
        </div>
        <button className="btn" onClick={() => setShow(true)}>+ Add milestone</button>
      </div>

      {p.milestones.length === 0 && <div className="empty">No milestones yet.</div>}

      {p.milestones.map((m) => (
        <div className={`milestone ${m.status}`} key={m.id}>
          <div className="dot" />
          <div className="body">
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
              <div className="mt">{m.title}</div>
              <div className="amount">â‚¹{(m.amount || 0).toLocaleString("en-IN")}</div>
            </div>
            <div className="md">{m.description}</div>
            <div className="md">
              Due: <b>{m.due_date || "â€”"}</b> Â· Status: <span className={`badge ${m.status}`} style={{ marginLeft: 4 }}>{m.status}</span>
            </div>
            <div className="actions">
              {m.status === "pending" && (
                <button className="btn ghost sm" onClick={() => setStatus(m, "in_progress")}>
                  â–¶ Start
                </button>
              )}
              {m.status === "in_progress" && (
                <button className="btn ghost sm" onClick={() => setStatus(m, "completed")}>
                  <Check size={12} style={{ display: "inline", verticalAlign: "-2px" }} /> Mark completed
                </button>
              )}
              {m.status !== "approved" && (
                <button className="btn sm" onClick={() => setStatus(m, "approved")}>
                  <Check size={12} style={{ display: "inline", verticalAlign: "-2px" }} /> Approve &amp; release payment
                </button>
              )}
              {m.status === "approved" && (
                <span className="badge approved">approved â€” synced to PayPal (Person 1)</span>
              )}
              <button className="btn danger sm" onClick={() => remove(m)}>
                <X size={13} />
              </button>
            </div>
          </div>
        </div>
      ))}

      <div className="card" style={{ marginTop: 18 }}>
        <h3>How this connects to payments</h3>
        <div className="meta" style={{ marginTop: 8 }}>
          When a milestone is <b style={{ color: "var(--accent)" }}>approved</b>, it appears on{" "}
          <code>GET /api/milestones/approved</code> â€” Person 1's Core Platform polls this endpoint and triggers the PayPal
          payout for that amount. Contract source: Person 2's ContractFlow (<code>{p.contract_ref || "n/a"}</code>).
        </div>
      </div>

      {show && (
        <Modal title="Add milestone" onClose={() => setShow(false)}>
          <div className="field">
            <label>Title *</label>
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Design completion" autoFocus />
          </div>
          <div className="field">
            <label>Description</label>
            <textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="field-row">
            <div className="field">
              <label>Due date</label>
              <input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
            </div>
            <div className="field">
              <label>Payment amount (â‚¹)</label>
              <input type="number" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} placeholder="7000" />
            </div>
          </div>
          <div className="modal-actions">
            <button className="btn ghost" onClick={() => setShow(false)}>Cancel</button>
            <button className="btn" onClick={create}>Add milestone</button>
          </div>
        </Modal>
      )}
    </div>
  );
}
