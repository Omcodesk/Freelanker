import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft as ArrowLeftIcon, Check, RotateCcw, Upload } from "lucide-react";
import { api, BASE_URL } from "../api";

export default function Deliverables({ toast }) {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [title, setTitle] = useState("");
  const [by, setBy] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState({});
  const inputRef = useRef(null);

  const load = () => api.get(`/api/projects/${id}`).then(setP).catch(() => {});
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (!p) return <div className="empty">Loadingâ€¦</div>;

  const upload = async () => {
    if (!file || !title.trim()) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("title", title.trim());
      fd.append("submitted_by", by.trim() || "Team");
      fd.append("file", file);
      await api.upload(`/api/projects/${p.id}/deliverables`, fd);
      setTitle("");
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      load();
      toast("Deliverable uploaded â€” awaiting client review");
    } catch (e) {
      toast(e.message);
    } finally {
      setBusy(false);
    }
  };

  const review = async (d, status) => {
    await api.put(`/api/deliverables/${d.id}/review`, {
      status,
      review_note: note[d.id] || (status === "approved" ? "Approved by client" : "Please revise"),
    });
    load();
    toast(status === "approved" ? `"${d.title}" approved` : `Revision requested on "${d.title}"`);
  };

  const counts = {
    submitted: p.deliverables.filter((d) => d.status === "submitted").length,
    approved: p.deliverables.filter((d) => d.status === "approved").length,
    revision: p.deliverables.filter((d) => d.status === "revision_requested").length,
  };

  return (
    <div>
      <Link to={`/projects/${p.id}`} className="back-link"><ArrowLeftIcon /> {p.name}</Link>
      <div className="section-head">
        <div>
          <h2 style={{ fontSize: 20 }}>Deliverables Upload & Review</h2>
          <div className="page-sub">
            {counts.submitted} awaiting review Â· {counts.approved} approved Â· {counts.revision} in revision
          </div>
        </div>
      </div>

      <div className="dropzone">
        <Upload size={26} style={{ marginBottom: 6 }} />
        <b>Submit a deliverable</b>
        <div style={{ fontSize: 12.5, margin: "6px 0 14px" }}>Upload finished work files for client review</div>
        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 10, maxWidth: 620, margin: "0 auto", textAlign: "left" }}>
          <div className="field" style={{ margin: 0 }}>
            <label>Title *</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Homepage design v2" />
          </div>
          <div className="field" style={{ margin: 0 }}>
            <label>Submitted by</label>
            <input value={by} onChange={(e) => setBy(e.target.value)} placeholder="Freelancer name" />
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <input
            ref={inputRef}
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            style={{ maxWidth: 420, margin: "0 auto", display: "block", width: "100%" }}
          />
        </div>
        <button className="btn" style={{ marginTop: 14 }} disabled={busy || !file || !title.trim()} onClick={upload}>
          {busy ? "Uploadingâ€¦" : "Upload deliverable"}
        </button>
      </div>

      {p.deliverables.length === 0 && <div className="empty">No deliverables submitted yet.</div>}

      {p.deliverables.map((d) => (
        <div className="deliverable" key={d.id}>
          <div>
            <div className="dt">
              {d.title} <span className="badge pending" style={{ marginLeft: 6 }}>v{d.version}</span>
            </div>
            <div className="dm">
              {d.filename} Â· by <b>{d.submitted_by || "â€”"}</b> Â·{" "}
              {d.created_at ? new Date(d.created_at).toLocaleString() : ""}
              {d.review_note ? <> · note: “{d.review_note}”</> : null}
            </div>
            <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center" }}>
              <span className={`badge ${d.status}`}>{d.status.replace("_", " ")}</span>
              {d.filepath && (
                <a className="btn ghost sm" href={BASE_URL + d.filepath} target="_blank" rel="noreferrer">
                  Open file
                </a>
              )}
            </div>
          </div>
          <div style={{ minWidth: 230 }}>
            <input
              placeholder="Review noteâ€¦"
              value={note[d.id] || ""}
              onChange={(e) => setNote({ ...note, [d.id]: e.target.value })}
              style={{ marginBottom: 8 }}
            />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button className="btn ghost sm" onClick={() => review(d, "revision_requested")}>
                â†© Request revision
              </button>
              <button className="btn sm" onClick={() => review(d, "approved")}>
                <Check size={12} style={{ display: "inline", verticalAlign: "-2px" }} /> Approve
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
