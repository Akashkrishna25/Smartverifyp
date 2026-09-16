import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import {
  LayoutDashboard, FileText, Upload, CheckCircle,
  BarChart3, LogOut, ShieldCheck, Users, Landmark
} from "lucide-react";

const nav = [
  { to: "/dashboard",    label: "Dashboard",    icon: LayoutDashboard },
  { to: "/applications", label: "Applications", icon: FileText },
  { to: "/upload",       label: "Upload Documents",  icon: Upload },
  { to: "/gov-verify",   label: "Gov Verification",  icon: Landmark },
  { to: "/verify",       label: "Verify",       icon: CheckCircle },
  { to: "/reports",      label: "Reports",      icon: BarChart3 },
];

const adminNav = [
  { to: "/admin/users",  label: "Users",        icon: Users },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => { logout(); navigate("/login"); };

  return (
    <aside className="fixed inset-y-0 left-0 w-64 bg-primary-900 text-white flex flex-col z-30">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-primary-700">
        <ShieldCheck className="w-8 h-8 text-blue-300" />
        <div>
          <p className="font-bold text-lg leading-tight">SmartVerify</p>
          <p className="text-xs text-blue-300">AI Loan Verification</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to} to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-primary-600 text-white"
                  : "text-blue-200 hover:bg-primary-700 hover:text-white"
              }`
            }
          >
            <Icon className="w-5 h-5" />
            {label}
          </NavLink>
        ))}

        {user?.role === "admin" && (
          <>
            <div className="pt-4 pb-1 px-3 text-xs text-blue-400 uppercase tracking-wider">Admin</div>
            {adminNav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to} to={to}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive ? "bg-primary-600 text-white" : "text-blue-200 hover:bg-primary-700 hover:text-white"
                  }`
                }
              >
                <Icon className="w-5 h-5" />
                {label}
              </NavLink>
            ))}
          </>
        )}
      </nav>

      {/* User footer */}
      <div className="px-4 py-4 border-t border-primary-700">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-full bg-primary-600 flex items-center justify-center text-sm font-bold">
            {user?.name?.[0]?.toUpperCase() || "U"}
          </div>
          <div className="overflow-hidden">
            <p className="text-sm font-medium truncate">{user?.name || "User"}</p>
            <p className="text-xs text-blue-300 capitalize">{user?.role?.replace("_", " ")}</p>
          </div>
        </div>
        <button onClick={handleLogout}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-blue-200 hover:bg-primary-700 hover:text-white transition-colors">
          <LogOut className="w-4 h-4" /> Sign out
        </button>
      </div>
    </aside>
  );
}
