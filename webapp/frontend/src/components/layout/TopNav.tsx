import { NavLink } from "react-router-dom";
import { LayoutDashboard, Search, Briefcase, History, Settings } from "lucide-react";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/assets", label: "Assets", icon: Search },
  { to: "/portfolio", label: "Portfolio", icon: Briefcase },
  { to: "/history", label: "History", icon: History },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function TopNav() {
  return (
    <nav className="border-b border-[#222] bg-[#111] px-6 h-14 flex items-center justify-between">
      <div className="flex items-center gap-8">
        <span className="text-white font-bold text-lg tracking-tight">AI Hedge Fund</span>
        <div className="flex gap-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors ${
                  isActive ? "bg-[#1a1a1a] text-white" : "text-[#666] hover:text-[#999]"
                }`
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
}
