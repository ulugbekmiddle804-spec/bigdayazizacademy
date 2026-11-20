import { AnimatePresence, domAnimation, LazyMotion } from "framer-motion";
import { lazy, Suspense } from "react";
import { Route, Routes, useLocation } from "react-router-dom";

import { Loader } from "./components/Loader";
import { Toaster } from "./components/Toast";
import { EntryPage } from "./pages/EntryPage";

// Code splitting: the exam, result and admin screens load only when needed.
const ExamPage = lazy(() => import("./pages/ExamPage"));
const DonePage = lazy(() => import("./pages/DonePage"));
const AdminApp = lazy(() => import("./admin/AdminApp"));
const NotFound = lazy(() => import("./pages/NotFound"));

export function App() {
  const location = useLocation();
  const area = location.pathname.startsWith("/admin") ? "admin" : location.pathname;
  return (
    <LazyMotion features={domAnimation} strict>
      <Toaster />
      <Suspense fallback={<div className="page-center"><Loader /></div>}>
        <AnimatePresence mode="wait">
          <Routes location={location} key={area}>
            <Route path="/" element={<EntryPage />} />
            <Route path="/test" element={<ExamPage />} />
            <Route path="/done" element={<DonePage />} />
            <Route path="/admin/*" element={<AdminApp />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AnimatePresence>
      </Suspense>
    </LazyMotion>
  );
}
