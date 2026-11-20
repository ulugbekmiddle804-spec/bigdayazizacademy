export function Loader({ label = "Yuklanmoqda..." }: { label?: string }) {
  return (
    <div className="loader" role="status">
      <div className="loader-orbit">
        <span />
        <span />
        <span />
      </div>
      <p className="muted">{label}</p>
    </div>
  );
}
