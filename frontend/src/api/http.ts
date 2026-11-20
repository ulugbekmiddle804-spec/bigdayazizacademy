export class ApiError extends Error {
  status: number;
  code?: string;
  data: unknown;

  constructor(status: number, message: string, data: unknown, code?: string) {
    super(message);
    this.status = status;
    this.data = data;
    this.code = code;
  }

  get isNetwork() {
    return this.status === 0;
  }
}

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp("(?:^|; )" + name.replace(/[.$?*|{}()[\]\\/+^]/g, "\\$&") + "=([^;]*)"));
  return match ? decodeURIComponent(match[1]) : null;
}

export function firstErrorMessage(data: unknown, fallback = "Xatolik yuz berdi. Qaytadan urinib ko'ring."): string {
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (Array.isArray(data)) return firstErrorMessage(data[0], fallback);
  if (typeof data === "object") {
    const obj = data as Record<string, unknown>;
    if (typeof obj.detail === "string") return obj.detail;
    for (const value of Object.values(obj)) {
      const msg = firstErrorMessage(value, "");
      if (msg) return msg;
    }
  }
  return fallback;
}

export interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  timeoutMs?: number;
  keepalive?: boolean;
  csrf?: boolean;
  signal?: AbortSignal;
}

export async function request<T>(url: string, opts: RequestOptions = {}): Promise<T> {
  const method = opts.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json", ...(opts.headers ?? {}) };
  let body: BodyInit | undefined;
  if (opts.body instanceof FormData) {
    body = opts.body;
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  if (opts.csrf && method !== "GET") {
    const token = readCookie("csrftoken");
    if (token) headers["X-CSRFToken"] = token;
  }
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), opts.timeoutMs ?? 15000);
  opts.signal?.addEventListener("abort", () => controller.abort());
  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body,
      credentials: "same-origin",
      keepalive: opts.keepalive,
      signal: controller.signal,
    });
  } catch {
    throw new ApiError(0, "Internet aloqasi yo'q yoki server javob bermayapti.", null);
  } finally {
    window.clearTimeout(timer);
  }
  const type = response.headers.get("content-type") ?? "";
  const data = type.includes("application/json") ? await response.json().catch(() => null) : null;
  if (!response.ok) {
    const code = data && typeof data === "object" ? ((data as Record<string, unknown>).code as string) : undefined;
    let message = firstErrorMessage(data);
    if (response.status === 429) message = "So'rovlar juda ko'p. Bir oz kutib, qayta urinib ko'ring.";
    if (response.status >= 500) message = "Serverda vaqtinchalik xatolik. Birozdan so'ng qayta urinib ko'ring.";
    throw new ApiError(response.status, message, data, code);
  }
  return data as T;
}

export async function downloadFile(url: string, fallbackName: string) {
  const response = await fetch(url, { credentials: "same-origin" });
  if (!response.ok) throw new ApiError(response.status, "Faylni yuklab bo'lmadi.", null);
  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/);
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = match ? match[1] : fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 2000);
}
