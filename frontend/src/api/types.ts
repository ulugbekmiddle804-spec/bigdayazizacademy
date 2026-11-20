export interface StageInfo {
  number: number;
  title: string;
  question_count: number;
  duration_minutes: number;
}

export interface SubjectNode {
  id: number;
  name: string;
  slug: string;
  description: string;
  icon: string;
  selectable: boolean;
  stages: StageInfo[];
  children: SubjectNode[];
}

export interface Meta {
  branches: { id: number; name: string; address: string }[];
  subjects: SubjectNode[];
  site: { title: string; registration_open: boolean };
}

export interface OptionItem {
  id: string;
  text: string;
}

export interface QuestionItem {
  id: number;
  position: number;
  text: string;
  options: OptionItem[];
  selected: string | null;
}

export interface AttemptStageState {
  number: number;
  title: string;
  question_count: number;
  duration_seconds: number;
  started_at: string | null;
  deadline: string | null;
  finished: boolean;
  finish_reason: string | null;
}

export interface ResultSummary {
  total_score: number;
  max_score: number;
  percent: number;
  correct: number;
  wrong: number;
  blank: number;
  question_total: number;
  stages: { number: number; title: string; score: number; max_score: number; correct: number; total: number }[];
}

export interface ReviewItem {
  stage: number;
  position: number;
  text: string;
  options: OptionItem[];
  selected: string | null;
  correct: string;
}

export interface AttemptState {
  id: string;
  status: "active" | "completed" | "annulled";
  first_name: string;
  last_name: string;
  branch: string;
  subject: string;
  current_stage: number;
  server_time: string;
  stages: AttemptStageState[];
  questions: QuestionItem[];
  result: ResultSummary | null;
  review: ReviewItem[] | null;
}
