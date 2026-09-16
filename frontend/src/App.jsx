import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "./context/AuthContext";

import Layout       from "./components/layout/Layout";
import PrivateRoute from "./components/auth/PrivateRoute";

import LoginPage       from "./pages/LoginPage";
import DashboardPage   from "./pages/DashboardPage";
import ApplicationsPage from "./pages/ApplicationsPage";
import UploadPage      from "./pages/UploadPage";
import VerifyPage           from "./pages/VerifyPage";
import ReportsPage          from "./pages/ReportsPage";
import GovVerificationPage  from "./pages/GovVerification";
import ReportViewPage       from "./pages/ReportViewPage";
import UsersPage            from "./pages/UsersPage";

function PrivateLayout({ children }) {
  return (
    <PrivateRoute>
      <Layout>{children}</Layout>
    </PrivateRoute>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          <Route path="/dashboard"    element={<PrivateLayout><DashboardPage /></PrivateLayout>} />
          <Route path="/applications" element={<PrivateLayout><ApplicationsPage /></PrivateLayout>} />
          <Route path="/upload"       element={<PrivateLayout><UploadPage /></PrivateLayout>} />
          <Route path="/verify"       element={<PrivateLayout><VerifyPage /></PrivateLayout>} />
          <Route path="/gov-verify"   element={<PrivateLayout><GovVerificationPage /></PrivateLayout>} />
          <Route path="/gov-verify/:appId"   element={<PrivateLayout><GovVerificationPage /></PrivateLayout>} />
          <Route path="/reports"      element={<PrivateLayout><ReportsPage /></PrivateLayout>} />
          <Route path="/report/:appId" element={<PrivateLayout><ReportViewPage /></PrivateLayout>} />
          <Route path="/admin/users"  element={<PrivateLayout><UsersPage /></PrivateLayout>} />

          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
