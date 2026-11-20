import { Icon } from "../../components/Icon";

export function Pagination({ count, page, pageSize, onChange }: { count: number; page: number; pageSize: number; onChange: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (pages <= 1) return null;
  const nums: (number | "…")[] = [];
  for (let i = 1; i <= pages; i++) {
    if (i === 1 || i === pages || Math.abs(i - page) <= 1) nums.push(i);
    else if (nums[nums.length - 1] !== "…") nums.push("…");
  }
  return (
    <nav className="pagination" aria-label="Sahifalar">
      <button className="icon-btn" disabled={page <= 1} onClick={() => onChange(page - 1)} aria-label="Oldingi">
        <Icon name="left" size={16} />
      </button>
      {nums.map((n, i) =>
        n === "…" ? (
          <span key={`e${i}`} className="muted">…</span>
        ) : (
          <button key={n} className={`page-btn${n === page ? " active" : ""}`} onClick={() => onChange(n)}>
            {n}
          </button>
        ),
      )}
      <button className="icon-btn" disabled={page >= pages} onClick={() => onChange(page + 1)} aria-label="Keyingi">
        <Icon name="right" size={16} />
      </button>
    </nav>
  );
}
