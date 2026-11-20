export function Logo({ title = "Aziz Academy" }: { title?: string }) {
  return (
    <div className="logo">
      <img className="logo-img" src="/logo.png" alt="" width={36} height={36} />
      <span className="logo-text">{title}</span>
    </div>
  );
}
