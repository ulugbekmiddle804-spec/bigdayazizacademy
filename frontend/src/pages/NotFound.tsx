import { Link } from "react-router-dom";

import { Background } from "../components/Background";
import { PageTransition } from "../components/PageTransition";

export default function NotFound() {
  return (
    <PageTransition className="page-center">
      <Background />
      <div className="glass" style={{ padding: 40, textAlign: "center", maxWidth: 420 }}>
        <h1 className="gradient-text" style={{ fontSize: "4rem" }}>404</h1>
        <p className="muted" style={{ margin: "8px 0 24px" }}>Sahifa topilmadi.</p>
        <Link to="/" className="btn btn-primary">Bosh sahifa</Link>
      </div>
    </PageTransition>
  );
}
