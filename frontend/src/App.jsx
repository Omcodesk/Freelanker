import { useCallback, useRef, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import ProjectDetails from "./pages/ProjectDetails";
import Tasks from "./pages/Tasks";
import Milestones from "./pages/Milestones";
import Collaboration from "./pages/Collaboration";
import Deliverables from "./pages/Deliverables";

function ToastHost({ msg }) {
  if (!msg) return null;
  return <div className="toast">{msg}</div>;
}

export default function App() {
  const [msg, setMsg] = useState("");
  const timer = useRef(null);

  const toast = useCallback((text) => {
    setMsg(text);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setMsg(""), 3200);
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard toast={toast} />} />
          <Route path="/projects/:id" element={<ProjectDetails toast={toast} />} />
          <Route path="/projects/:id/tasks" element={<Tasks toast={toast} />} />
          <Route path="/projects/:id/milestones" element={<Milestones toast={toast} />} />
          <Route path="/projects/:id/collaboration" element={<Collaboration toast={toast} />} />
          <Route path="/projects/:id/deliverables" element={<Deliverables toast={toast} />} />
        </Route>
      </Routes>
      <ToastHost msg={msg} />
    </BrowserRouter>
  );
}
