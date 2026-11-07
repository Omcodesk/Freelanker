import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Bell, ArrowLeft as ArrowLeftIcon } from "lucide-react";
import { api } from "../api";

export default function Collaboration({ toast }) {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [body, setBody] = useState("");
  const [author, setAuthor] = useState("");
  const [role, setRole] = useState("client");

  const load = () => api.get(`/api/projects/${id}`).then(setP).catch(() => {});
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (!p) return <div className="empty">Loadingâ€¦</div>;

  const send = async () => {
    if (!body.trim() || !author.trim()) return;
    await api.post(`/api/projects/${p.id}/comments`, { author, role, body: body.trim() });
    setBody("");
    load();
    toast("Message posted");
  };

  return (
    <div>
      <Link to={`/projects/${p.id}`} className="back-link"><ArrowLeftIcon /> {p.name}</Link>
      <div className="section-head">
        <div>
          <h2 style={{ fontSize: 20 }}>Team Collaboration</h2>
          <div className="page-sub">Comments & updates between client and freelancer</div>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 300px", gap: 16 }}>
        <div className="card">
          <h3>Discussion ({p.comments.length})</h3>
          <div style={{ marginTop: 8 }}>
            {p.comments.length === 0 && <div className="empty">No messages yet â€” start the conversation.</div>}
            {p.comments.map((c) => (
              <div className="comment" key={c.id}>
                <div className="avatar">{c.author[0]?.toUpperCase()}</div>
                <div style={{ flex: 1 }}>
                  <div>
                    <span className="who">{c.author}</span>
                    <span className="role">{c.role}</span>
                    <span className="when" style={{ float: "right" }}>
                      {c.created_at ? new Date(c.created_at).toLocaleString() : ""}
                    </span>
                  </div>
                  <div className="body">{c.body}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="composer">
            <textarea
              placeholder={author ? "Write a messageâ€¦" : "Enter your name below to postâ€¦"}
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
            <button className="btn" onClick={send} style={{ alignSelf: "flex-end" }}>Send</button>
          </div>
        </div>

        <div className="card" style={{ alignSelf: "start" }}>
          <h3>Posting as</h3>
          <div className="field" style={{ marginTop: 12 }}>
            <label>Your name</label>
            <input value={author} onChange={(e) => setAuthor(e.target.value)} placeholder="e.g. Priya Sharma" />
          </div>
          <div className="field">
            <label>Role</label>
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="client">Client</option>
              <option value="freelancer">Freelancer</option>
              <option value="member">Team member</option>
            </select>
          </div>
          <div className="meta">
            Everyone on the project sees these messages. Important updates also appear in the{" "}
            <Bell size={13} style={{ display: "inline", verticalAlign: "-2px" }} /> notification bell.
          </div>
        </div>
      </div>
    </div>
  );
}
