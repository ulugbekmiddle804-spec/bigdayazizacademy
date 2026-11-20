import { request } from "./http";
import type { AttemptState, Meta } from "./types";

export interface AnswerItem {
  id: number;
  option: string | null;
}

const auth = (token: string) => ({ "X-Attempt-Token": token });

export const examApi = {
  meta: () => request<Meta>("/api/public/meta/"),
  start: (body: { first_name: string; last_name: string; branch_id: number; subject_id: number }) =>
    request<{ token: string; state: AttemptState }>("/api/attempts/", { method: "POST", body }),
  state: (id: string, token: string) => request<AttemptState>(`/api/attempts/${id}/`, { headers: auth(token) }),
  save: (id: string, token: string, stage: number, answers: AnswerItem[], keepalive = false) =>
    request<{ saved: number; server_time: string }>(`/api/attempts/${id}/answers/`, {
      method: "PUT",
      body: { stage, answers },
      headers: auth(token),
      keepalive,
      timeoutMs: 12000,
    }),
  finishStage: (id: string, token: string, stage: number, answers: AnswerItem[]) =>
    request<AttemptState>(`/api/attempts/${id}/stages/${stage}/finish/`, {
      method: "POST",
      body: { answers },
      headers: auth(token),
      timeoutMs: 20000,
    }),
  startStage: (id: string, token: string, stage: number) =>
    request<AttemptState>(`/api/attempts/${id}/stages/${stage}/start/`, { method: "POST", body: {}, headers: auth(token) }),
};
