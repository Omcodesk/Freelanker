import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { IndianRupee } from "lucide-react";
import { api } from "../api";
import Progress from "../components/Progress";
import Modal from "../components/Modal";

export default function Dashboard({ toast }) {
  const [projects, setProjects] = useState([]);
  const [filter, setFilter] = useState("all");
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
    client_name: "",
    freelancer_name: "",
    budget: "",
  });
  const nav = useNavigate();

  const load = () => api.get("/api/projects").then(setProjects).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    if (!form.name.trim()) return;
    const p = await api.post("/api/projects", {
      ...form,
      budget: Number(form.budget) || 0,
      members: [],
    });
    setShow(false);
    toast("Project created");
    nav(`/projects/${p.id}`);
  };

  const list = projects.filter((p) => filter === "all" || p.status === filter);
  const totalBudget = projects.reduce((s, p) => s + (p.budget || 0), 0);
  const totalTasks = projects.reduce((s, p) => s + p.tasks_total, 0);
  const totalDone = projects.reduce((s, p) => s + p.tasks_done, 0);

  return (
    <div>
      <div className="stats">
        <div className="stat">
          <div className="v">{projects.length}</div>
          <div className="l">Active projects</div>
        </div>
        <div className="stat">
          <div className="v">
            {totalDone}/{totalTasks}
          </div>
          <div className="l">Tasks completed</div>
        </div>
        <div className="stat">
          <div className="v">₹{totalBudget.toLocaleString("en-IN")}</div>
          <div className="l">Total budget</div>
        </div>
        <div className="stat">
          <div className="v">{projects.reduce((s, p) => s + p.milestones_approved, 0)}</div>
          <div className="l">Milestones approved</div>
        </div>
      </div>

      <div className="section-head">
        <div className="filters">
          {["all", "active", "completed", "paused"].map((f) => (
            <button key={f} className={`chip ${filter === f ? "active" : ""}`} onClick={() => setFilter(f)}>
              {f}
            </button>
          ))}
        </div>
        <button className="btn" onClick={() => setShow(true)}>
          + New Project
        </button>
      </div>

      {list.length === 0 ? (
        <div className="empty">No projects yet. Create one to start managing work.</div>
      ) : (
        <div className="grid cols-3">
          {list.map((p) => (
            <Link key={p.id} to={`/projects/${p.id}`} className="card project-card">
              <div className="row">
                <div className="name">{p.name}</div>
                <span className={`badge ${p.status}`}>{p.status}</span>
              </div>
              <div className="meta">
                Client: <b>{p.client_name || "—"}</b>
                <br />
                Freelancer: <b>{p.freelancer_name || "—"}</b>
                <br />
                <IndianRupee size={13} style={{ display: "inline", verticalAlign: "-2px" }} />{" "}
                {(p.budget || 0).toLocaleString("en-IN")} · {p.milestones_approved}/{p.milestones_total} milestones approved
              </div>
              <Progress value={p.progress} done={p.tasks_done} total={p.tasks_total} />
            </Link>
          ))}
        </div>
      )}

      {show && (
        <Modal title="Create project" onClose={() => setShow(false)}>
          <div className="field">
            <label>Project name *</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Website Development" autoFocus />
          </div>
          <div className="field">
            <label>Description</label>
            <textarea rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="What is this project about?" />
          </div>
          <div className="field-row">
            <div className="field">
              <label>Client</label>
              <input value={form.client_name} onChange={(e) => setForm({ ...form, client_name: e.target.value })} />
            </div>
            <div className="field">
              <label>Freelancer</label>
              <input value={form.freelancer_name} onChange={(e) => setForm({ ...form, freelancer_name: e.target.value })} />
            </div>
          </div>
          <div className="field">
            <label>Budget (₹)</label>
            <input type="number" value={form.budget} onChange={(e) => setForm({ ...form, budget: e.target.value })} placeholder="20000" />
          </div>
          <div className="modal-actions">
            <button className="btn ghost" onClick={() => setShow(false)}>Cancel</button>
            <button className="btn" onClick={create}>Create project</button>
          </div>
        </Modal>
      )}
    </div>
  );
}
