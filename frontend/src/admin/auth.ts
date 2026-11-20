import { create } from "zustand";

import type { AdminUser } from "./api";

interface AuthStore {
  user: AdminUser | null;
  setUser: (u: AdminUser | null) => void;
}

export const useAdminAuth = create<AuthStore>((set) => ({ user: null, setUser: (user) => set({ user }) }));
