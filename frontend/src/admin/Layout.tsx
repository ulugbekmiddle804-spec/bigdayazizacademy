import { useState, type ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";

import { Icon, type IconName } from "../components/Icon";
import { Logo } from "../components/Logo";
import { adminApi } from "./api";
import { useAdminAuth } from "./auth";

const links: { to: string; label: string; icon: IconName; end?: boolean }[] = [
  { to: "/admin", label: "Boshqaruv paneli", icon: "chart", end: true },
  { to: "/admin/results", label: "Natijalar", icon: "list" },
  { to: "/admin/questions", label: "Savollar", icon: "book" },
  { to: "/admin/subjects", label: "Fanlar va bosqichlar", icon: "layers" },
  { to: "/admin/branches", label: "Filiallar", icon: "building" },
  { to: "/admin/settings", label: "Sozlamalar", icon: "settings" },
];

export function AdminLayout({ children }: { children: ReactNode }) {
  const user = useAdminAuth((s) => s.user);
  const setUser = useAdminAuth((s) => s.setUser);
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  const logout = async () => {
    try {
      await adminApi.logout();
    } finally {
      setUser(null);
      navigate("/admin/login", { replace: true });
    }
  };

  return (
    <div className="admin">
      <aside className={`admin-side${open ? " open" : ""}`}>
        <div className="admin-brand">
          <Logo title="Aziz Academy" />
        </div>
        <nav>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} onClick={() => setOpen(false)}
              className={({ isActive }) => `admin-link${isActive ? " active" : ""}`}>
              <Icon name={l.icon} size={18} />
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="admin-user">
          <div>
            <span className="tiny">Kirgan</span>
            <strong>{user?.username}</strong>
          </div>
          <button className="icon-btn" onClick={logout} title="Chiqish" aria-label="Chiqish">
            <Icon name="logout" size={18} />
          </button>
        </div>
      </aside>
      {open && <div className="admin-scrim" onClick={() => setOpen(false)} />}
      <div className="admin-main">
        <header className="admin-topbar">
          <button className="icon-btn admin-menu" onClick={() => setOpen(true)} aria-label="Menyu">
            <Icon name="menu" size={18} />
          </button>
          <span className="muted tiny">{links.find((l) => (l.end ? location.pathname === l.to : location.pathname.startsWith(l.to)))?.label}</span>
          <a className="btn btn-sm btn-ghost" href="/" target="_blank" rel="noreferrer">
            <Icon name="eye" size={16} /> Saytni ochish
          </a>
        </header>
        <div className="admin-content">{children}</div>
      </div>
    </div>
  );
}
