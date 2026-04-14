import { useEffect, useState } from "react";

const WORDS = [
  "health",
  "access",
  "equity",
  "outcomes",
  "resilience",
  "coverage",
  "lives",
];

const TYPING_MS = 90;
const DELETING_MS = 50;
const PAUSE_MS = 2200;

export default function AnimatedTagline() {
  const [wordIdx, setWordIdx] = useState(0);
  const [text, setText] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const word = WORDS[wordIdx];
    let timer: ReturnType<typeof setTimeout>;

    if (!deleting && text === word) {
      timer = setTimeout(() => setDeleting(true), PAUSE_MS);
    } else if (deleting && text === "") {
      setDeleting(false);
      setWordIdx((i) => (i + 1) % WORDS.length);
    } else {
      timer = setTimeout(
        () => {
          setText(
            deleting
              ? word.slice(0, text.length - 1)
              : word.slice(0, text.length + 1)
          );
        },
        deleting ? DELETING_MS : TYPING_MS
      );
    }

    return () => clearTimeout(timer);
  }, [text, deleting, wordIdx]);

  return (
    <h1 className="hero-tagline">
      Predictive analytics for better{" "}
      <span className="hero-word">
        {text}
        <span className="hero-cursor" />
      </span>
    </h1>
  );
}
