import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Bell,
  CheckSquare,
  CircleDot,
  Diamond,
  LayoutGrid,
  MessageSquare,
  Upload,
} from "lucide-react";
import { api } from "../api";

function timeAgo(iso) {
  if (!iso) return "";
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export default function Layout() {
  const [notifs, setNotifs] = useState([]);
  const [open, setOpen] = useState(false);
  const [tick, setTick] = useState(0);
  const wrap = useRef(null);
  const loc = useLocation();

  useEffect(() => {
    let alive = true;
    const load = () =>
      api.get("/api/notifications").then((d) => alive && setNotifs(d)).catch(() => {});
    load();
    const id = setInterval(load, 8000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [tick]);

  useEffect(() => {
    const h = (e) => {
      if (wrap.current && !wrap.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const unread = notifs.filter((n) => !n.is_read).length;

  const toggle = async () => {
    const next = !open;
    setOpen(next);
    if (next && unread) {
      await api.post("/api/notifications/read", {});
      setTick((t) => t + 1);
    }
  };

  const isProject = /^\/projects\/\d+/.test(loc.pathname);
  const projectId = isProject ? loc.pathname.split("/")[2] : null;
  const base = `/projects/${projectId}`;

  const projectNav = isProject
    ? [
        { to: base, label: "Overview", Icon: CircleDot, end: true },
        { to: `${base}/tasks`, label: "Tasks", Icon: CheckSquare },
        { to: `${base}/milestones`, label: "Milestones", Icon: Diamond },
        { to: `${base}/collaboration`, label: "Collaboration", Icon: MessageSquare },
        { to: `${base}/deliverables`, label: "Deliverables", Icon: Upload },
      ]
    : [];

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">W</div>
          WorkBridge
        </div>
        <NavLink to="/" className={({ isActive }) => `nav-link ${isActive && !isProject ? "active" : ""}`} end>
          <LayoutGrid size={17} /> Projects
        </NavLink>
        {projectNav.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
            <n.Icon size={17} /> {n.label}
          </NavLink>
        ))}
        <div className="foot">
          <b>Person 3 module</b>
          FreelanceOS · Project management, collaboration & deliverables
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <div>
            <div className="page-title">{isProject ? "Project workspace" : "WorkBridge"}</div>
            <div className="page-sub">Manage work after the contract is approved</div>
          </div>
          <div className="bell-wrap" ref={wrap}>
            <button className="bell" onClick={toggle} title="Notifications">
              <Bell size={17} />
              {unread > 0 && <span className="dot">{unread}</span>}
            </button>
            {open && (
              <div className="notif-panel">
                {notifs.length === 0 && <div className="notif-empty">No notifications yet</div>}
                {notifs.map((n) => (
                  <div className="notif-item" key={n.id}>
                    <div className="t">{n.title}</div>
                    <div className="b">{n.body}</div>
                    <div className="time">{timeAgo(n.created_at)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        <Outlet context={{ refresh: () => setTick((t) => t + 1) }} />
      </main>
    </div>
  );
}
