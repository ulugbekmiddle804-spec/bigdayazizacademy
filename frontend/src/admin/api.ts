import { request } from "../api/http";

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AdminUser {
  username: string;
  is_superuser: boolean;
}

export interface Branch {
  id: number;
  name: string;
  address: string;
  is_active: boolean;
  sort_order: number;
  attempts_count: number;
}

export interface StageConfig {
  number: number;
  title: string;
  question_count: number;
  duration_minutes: number;
  source: "academic" | "subject";
  is_enabled: boolean;
}

export interface Subject {
  id: number;
  name: string;
  slug: string;
  parent: number | null;
  full_name: string;
  description: string;
  icon: string;
  is_academic: boolean;
  is_active: boolean;
  sort_order: number;
  stages: StageConfig[];
  question_counts: Record<string, number>;
  is_group: boolean;
}

export interface WordImportRequest {
  file: File;
  subject: number;
  stage: number;
  points: number;
  difficulty: string;
  replace: boolean;
  preview: boolean;
}

export interface WordImportResult {
  title: string;
  count: number;
  problems: { question: number; error: string }[];
  questions?: { number: number; text: string; options: string[]; correct: number | null }[];
  created?: number;
  replaced?: number;
}

export interface QuestionOption {
  id?: number;
  text: string;
  is_correct: boolean;
}

export interface Question {
  id: number;
  subject: number;
  subject_name: string;
  stage: number;
  text: string;
  difficulty: "easy" | "medium" | "hard";
  points: number;
  is_active: boolean;
  options: QuestionOption[];
  created_at: string;
  updated_at: string;
}

export interface AttemptRow {
  id: string;
  first_name: string;
  last_name: string;
  branch: number;
  branch_name: string;
  subject: number;
  subject_name: string;
  status: "active" | "completed" | "annulled";
  current_stage: number;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  stage1_score: number;
  stage1_correct: number;
  stage2_score: number;
  stage2_correct: number;
  total_score: number;
  max_score: number;
  percent: number;
  stage1_percent: number | null;
  stage2_percent: number | null;
  stage_count: number;
  correct_count: number;
  wrong_count: number;
  blank_count: number;
  question_total: number;
  retake_allowed: boolean;
}

export interface AttemptStageRow {
  number: number;
  title: string;
  question_count: number;
  duration_seconds: number;
  started_at: string | null;
  deadline: string | null;
  finished_at: string | null;
  finish_reason: string;
  score: number;
  max_score: number;
  correct_count: number;
  wrong_count: number;
  blank_count: number;
}

export interface AttemptAnswerRow {
  id: number;
  stage: number;
  position: number;
  question: number | null;
  question_text: string;
  options: { id: string; text: string }[];
  correct_option: string;
  selected_option: string | null;
  answered_at: string | null;
  is_correct: boolean | null;
  points: number;
  points_awarded: number;
  difficulty: string;
  result: "correct" | "wrong" | "blank" | "pending";
}

export interface AttemptDetail extends AttemptRow {
  ip_address: string | null;
  user_agent: string;
  stages: AttemptStageRow[];
  answers: AttemptAnswerRow[];
}

export interface Dashboard {
  attempts_total: number;
  completed_total: number;
  active_now: number;
  today: number;
  avg_percent: number | null;
  avg_duration: number;
  best_score: number | null;
  questions_total: number;
  branches_total: number;
  by_subject: { subject: string; count: number; avg_percent: number }[];
  by_branch: { branch: string; count: number; avg: number }[];
  daily: { date: string; count: number }[];
  warnings: { subject: string; stage: number; available: number; required: number }[];
  recent: AttemptRow[];
}

export interface SiteSettings {
  site_title: string;
  registration_open: boolean;
  show_score: boolean;
  show_answer_review: boolean;
  allow_retake: boolean;
  updated_at: string;
}

const A = "/api/admin";
const w = (method: string, body?: unknown) => ({ method, body, csrf: true });

export function qs(params: Record<string, string | number | undefined | null>) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

export const adminApi = {
  csrf: () => request<{ ok: boolean }>(`${A}/auth/csrf/`),
  me: () => request<AdminUser>(`${A}/auth/me/`),
  login: (username: string, password: string) => request<AdminUser>(`${A}/auth/login/`, w("POST", { username, password })),
  logout: () => request(`${A}/auth/logout/`, w("POST", {})),
  dashboard: () => request<Dashboard>(`${A}/dashboard/`),

  attempts: (params: Record<string, string | number | undefined>) =>
    request<Paginated<AttemptRow>>(`${A}/attempts/${qs(params)}`),
  attempt: (id: string) => request<AttemptDetail>(`${A}/attempts/${id}/`),
  allowRetake: (id: string, allowed: boolean) => request<AttemptRow>(`${A}/attempts/${id}/allow-retake/`, w("POST", { allowed })),
  annul: (id: string) => request<AttemptRow>(`${A}/attempts/${id}/annul/`, w("POST", {})),
  deleteAttempt: (id: string) => request(`${A}/attempts/${id}/`, w("DELETE")),
  deleteAttempts: (ids: string[]) => request<{ deleted: number }>(`${A}/attempts/bulk-delete/`, w("POST", { ids })),
  deleteAllAttempts: (filters: Record<string, string | number | undefined>) =>
    request<{ deleted: number }>(`${A}/attempts/bulk-delete/${qs(filters)}`, w("POST", { all: true, confirm: "DELETE" })),
  attemptsExportUrl: (params: Record<string, string | number | undefined>) => `${A}/attempts/export/${qs(params)}`,

  branches: () => request<Branch[]>(`${A}/branches/`),
  saveBranch: (b: Partial<Branch>) =>
    b.id ? request<Branch>(`${A}/branches/${b.id}/`, w("PATCH", b)) : request<Branch>(`${A}/branches/`, w("POST", b)),
  deleteBranch: (id: number) => request(`${A}/branches/${id}/`, w("DELETE")),

  subjects: () => request<Subject[]>(`${A}/subjects/`),
  saveSubject: (s: Partial<Subject>) =>
    s.id ? request<Subject>(`${A}/subjects/${s.id}/`, w("PATCH", s)) : request<Subject>(`${A}/subjects/`, w("POST", s)),
  deleteSubject: (id: number) => request(`${A}/subjects/${id}/`, w("DELETE")),

  questions: (params: Record<string, string | number | undefined>) =>
    request<Paginated<Question>>(`${A}/questions/${qs(params)}`),
  saveQuestion: (q: Partial<Question>) =>
    q.id ? request<Question>(`${A}/questions/${q.id}/`, w("PUT", q)) : request<Question>(`${A}/questions/`, w("POST", q)),
  patchQuestion: (id: number, data: Partial<Question>) => request<Question>(`${A}/questions/${id}/`, w("PATCH", data)),
  deleteQuestion: (id: number) => request(`${A}/questions/${id}/`, w("DELETE")),
  importQuestions: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ created: number }>(`${A}/questions/import/`, { method: "POST", body: fd, csrf: true, timeoutMs: 60000 });
  },
  questionsExportUrl: (params: Record<string, string | number | undefined>) => `${A}/questions/export/${qs(params)}`,
  templateUrl: `${A}/questions/template/`,
  wordTemplateUrl: `${A}/questions/word-template/`,
  importWord: (data: WordImportRequest) => {
    const fd = new FormData();
    fd.append("file", data.file);
    fd.append("subject", String(data.subject));
    fd.append("stage", String(data.stage));
    fd.append("points", String(data.points));
    fd.append("difficulty", data.difficulty);
    fd.append("replace", data.replace ? "1" : "0");
    fd.append("preview", data.preview ? "1" : "0");
    return request<WordImportResult>(`${A}/questions/import-word/`, { method: "POST", body: fd, csrf: true, timeoutMs: 60000 });
  },

  settings: () => request<SiteSettings>(`${A}/settings/`),
  saveSettings: (s: Partial<SiteSettings>) => request<SiteSettings>(`${A}/settings/`, w("PUT", s)),
};

export const fmt = {
  date: (iso: string | null) =>
    iso
      ? new Date(iso).toLocaleString("uz-UZ", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" })
      : "—",
  duration: (s: number | null) => {
    if (s === null || s === undefined) return "—";
    const h = Math.floor(s / 3600);
    const mnt = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return h ? `${h}:${String(mnt).padStart(2, "0")}:${String(sec).padStart(2, "0")}` : `${mnt}:${String(sec).padStart(2, "0")}`;
  },
};

export const statusLabel: Record<string, string> = { active: "Jarayonda", completed: "Yakunlangan", annulled: "Bekor qilingan" };
export const difficultyLabel: Record<string, string> = { easy: "Oson", medium: "O'rta", hard: "Qiyin" };
