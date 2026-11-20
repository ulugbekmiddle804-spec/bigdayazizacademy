const glyphs: Record<string, string> = {
  english: "En",
  russian: "Ру",
  math: "∑",
  arabic: "ع",
  uzbek: "Oʻz",
  oriental: "東",
  korean: "한",
  turkish: "Tr",
  chemistry: "H₂O",
  biology: "DNK",
  mental: "∞",
  nursing: "✚",
  primary: "ABC",
  history: "Tx",
  other: "•••",
  academic: "IQ",
  it: "</>",
  frontend: "</>",
  backend: "{ }",
  book: "Aa",
};

const tints: Record<string, string> = {
  english: "#0a16f0",
  russian: "#0a16f0",
  math: "#0a16f0",
  arabic: "#0a16f0",
  uzbek: "#0a16f0",
  oriental: "#0a16f0",
  it: "#0a16f0",
  frontend: "#0a16f0",
  backend: "#0a16f0",
  korean: "#0a16f0",
  turkish: "#0a16f0",
  chemistry: "#0a16f0",
  biology: "#0a16f0",
  mental: "#0a16f0",
  nursing: "#0a16f0",
  primary: "#0a16f0",
  history: "#0a16f0",
  other: "#0a16f0",
  academic: "#16a34a",
};

export function SubjectGlyph({ icon, size = 48 }: { icon: string; size?: number }) {
  return (
    <span
      className="subject-glyph"
      style={{ width: size, height: size, background: tints[icon] ?? tints.it, fontSize: size * 0.38 }}
      aria-hidden="true"
    >
      {glyphs[icon] ?? glyphs.book}
    </span>
  );
}
