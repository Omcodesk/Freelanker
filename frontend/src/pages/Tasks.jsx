import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Calendar, Check, X } from "lucide-react";
import { api } from "../api";
import Modal from "../components/Modal";

const COLS = [
  { key: "todo", label: "To do" },
  { key: "in_progress", label: "In progress" },
  { key: "done", label: "Done" },
];

export default function Tasks({ toast }) {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({
    title: "",
    description: "",
    assignee: "",
    priority: "medium",
    due_date: "",
  });

  const load = () => api.get(`/api/projects/${id}`).then(setP).catch(() => {});
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (!p) return <div className="empty">Loadingâ€¦</div>;

  const create = async () => {
    if (!form.title.trim()) return;
    await api.post(`/api/projects/${p.id}/tasks`, form);
    setShow(false);
    setForm({ title: "", description: "", assignee: "", priority: "medium", due_date: "" });
    load();
    toast("Task added");
  };

  const move = async (t, status) => {
    await api.put(`/api/tasks/${t.id}`, { status });
    load();
    if (status === "done") toast(`"${t.title}" completed`);
  };

  const remove = async (t) => {
    await api.del(`/api/tasks/${t.id}`);
    load();
    toast("Task deleted");
  };

  const assignees = p.members.map((m) => m.name);

  return (
    <div>
      <Link to={`/projects/${p.id}`} className="back-link"><ArrowLeftIcon /> {p.name}</Link>
      <div className="section-head">
        <div>
          <h2 style={{ fontSize: 20 }}>Task Management</h2>
          <div className="page-sub">
            {p.tasks_done}/{p.tasks_total} completed Â· {p.progress}%
          </div>
        </div>
        <button className="btn" onClick={() => setShow(true)}>+ Add task</button>
      </div>

      <div className="kanban">
        {COLS.map((col) => {
          const items = p.tasks.filter((t) => t.status === col.key);
          return (
            <div className="kanban-col" key={col.key}>
              <h4>
                {col.label} <span>{items.length}</span>
              </h4>
              {items.length === 0 && <div className="empty" style={{ padding: 18 }}>No tasks</div>}
              {items.map((t) => (
                <div className="task-card" key={t.id}>
                  <div className="tt">{t.title}</div>
                  {t.description && <div className="meta" style={{ fontSize: 12.5, marginBottom: 8 }}>{t.description}</div>}
                  <div className="tm">
                    <span className={`badge ${t.priority}`}>{t.priority}</span>
                    <span>{t.assignee || "unassigned"}</span>
                  </div>
                  <div className="tm" style={{ marginTop: 6 }}>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
                      <Calendar size={12} /> {t.due_date || "no due date"}
                    </span>
                  </div>
                  <div className="task-actions">
                    {col.key !== "todo" && (
                      <button className="btn ghost sm" onClick={() => move(t, col.key === "done" ? "in_progress" : "todo")}>
                        <ArrowLeft size={12} style={{ display: "inline", verticalAlign: "-2px" }} /> Back
                      </button>
                    )}
                    {col.key !== "done" && (
                      <button className="btn sm" onClick={() => move(t, col.key === "todo" ? "in_progress" : "done")}>
                        {col.key === "todo" ? (
                          <>
                            Start <ArrowRight size={12} style={{ display: "inline", verticalAlign: "-2px" }} />
                          </>
                        ) : (
                          <>
                            <Check size={12} style={{ display: "inline", verticalAlign: "-2px" }} /> Done
                          </>
                        )}
                      </button>
                    )}
                    <button className="btn danger sm" onClick={() => remove(t)}>
                      <X size={13} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </div>

      {show && (
        <Modal title="Add task" onClose={() => setShow(false)}>
          <div className="field">
            <label>Title *</label>
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} autoFocus />
          </div>
          <div className="field">
            <label>Description</label>
            <textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="field-row">
            <div className="field">
              <label>Assignee</label>
              <input list="assignees" value={form.assignee} onChange={(e) => setForm({ ...form, assignee: e.target.value })} placeholder="Who does this?" />
              <datalist id="assignees">
                {assignees.map((a) => (
                  <option key={a} value={a} />
                ))}
              </datalist>
            </div>
            <div className="field">
              <label>Priority</label>
              <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
          </div>
          <div className="field">
            <label>Due date</label>
            <input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
          </div>
          <div className="modal-actions">
            <button className="btn ghost" onClick={() => setShow(false)}>Cancel</button>
            <button className="btn" onClick={create}>Add task</button>
          </div>
        </Modal>
      )}
    </div>
  );
}
