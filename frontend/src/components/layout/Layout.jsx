import React, { useState } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";
import { useLocation } from "react-router-dom";

const PAGE_TITLES = {
  "/dashboard":    "Dashboard",
  "/applications": "Applications",
  "/upload":       "Upload Documents",
  "/verify":       "Verify Application",
  "/gov-verify":   "Government Verification",
  "/reports":      "Reports",
  "/admin/users":  "Users",
};

export default function Layout({ children }) {
  const { pathname } = useLocation();
  const title = PAGE_TITLES[pathname] || "SmartVerify";

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 ml-64">
        <Header title={title} />
        <main className="flex-1 p-6 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
