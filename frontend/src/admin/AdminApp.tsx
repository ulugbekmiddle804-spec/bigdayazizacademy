import { lazy, Suspense, useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import type { ApiError } from "../api/http";
import { Background } from "../components/Background";
import { Loader } from "../components/Loader";
import { adminApi } from "./api";
import { useAdminAuth } from "./auth";
import { AdminLayout } from "./Layout";
import { LoginPage } from "./pages/LoginPage";
import "./admin.css";

const Dashboard = lazy(() => import("./pages/DashboardPage"));
const Results = lazy(() => import("./pages/ResultsPage"));
const ResultDetail = lazy(() => import("./pages/ResultDetailPage"));
const Questions = lazy(() => import("./pages/QuestionsPage"));
const Subjects = lazy(() => import("./pages/SubjectsPage"));
const Branches = lazy(() => import("./pages/BranchesPage"));
const Settings = lazy(() => import("./pages/SettingsPage"));

export default function AdminApp() {
  const user = useAdminAuth((s) => s.user);
  const setUser = useAdminAuth((s) => s.setUser);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    adminApi
      .csrf()
      .then(() => adminApi.me())
      .then(setUser)
      .catch((e: ApiError) => {
        if (e.status === 401 || e.status === 403) setUser(null);
      })
      .finally(() => setChecking(false));
  }, [setUser]);

  if (checking) {
    return (
      <div className="page-center">
        <Background calm />
        <Loader />
      </div>
    );
  }

  if (!user) {
    return (
      <Routes>
        <Route path="login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/admin/login" replace />} />
      </Routes>
    );
  }

  return (
    <AdminLayout>
      <Suspense fallback={<Loader />}>
        <Routes>
          <Route index element={<Dashboard />} />
          <Route path="results" element={<Results />} />
          <Route path="results/:id" element={<ResultDetail />} />
          <Route path="questions" element={<Questions />} />
          <Route path="subjects" element={<Subjects />} />
          <Route path="branches" element={<Branches />} />
          <Route path="settings" element={<Settings />} />
          <Route path="login" element={<Navigate to="/admin" replace />} />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </Suspense>
    </AdminLayout>
  );
}
