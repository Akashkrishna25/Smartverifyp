import React from "react";
import { Bell, Menu } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export default function Header({ title, onMenuClick }) {
  const { user } = useAuth();
  return (
    <header className="sticky top-0 z-20 bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <button onClick={onMenuClick} className="lg:hidden p-1 rounded-lg hover:bg-slate-100">
          <Menu className="w-5 h-5" />
        </button>
        <h1 className="text-xl font-semibold text-slate-800">{title}</h1>
      </div>
      <div className="flex items-center gap-3">
        <button className="relative p-2 rounded-full hover:bg-slate-100">
          <Bell className="w-5 h-5 text-slate-500" />
        </button>
        <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center text-white text-sm font-bold">
          {user?.name?.[0]?.toUpperCase() || "U"}
        </div>
      </div>
    </header>
  );
}
