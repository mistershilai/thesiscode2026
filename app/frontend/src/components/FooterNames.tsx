import { useEffect, useState } from "react";

const NAMES = [
  "Elliot Lee",
  "Bartolomeo Stellato",
  "Stefan Clarke",
  "Gilbert Collins",
  "Hanna Ehrlich",
  "Khumo Seipone",
  "Lesego Busang",
  "Kabelo Kgongwana",
  "Stanley Mapiki",
  "Tiro Molefe",
  "Blessed Monyatsi",
  "Boseki Gaipone",
  "Atang Motlogelwa",
  "Ofentse Seosenyeng",
  "Bene D. Anand Paramadhas",
  "Seadingwane Kgotlele",
  "Tseleng Selabe",
  "Gaotlhalefshe Mosa Gaolekwe",
  "Celda Tirayakgosi",
  "Idah Seepo",
  "Teedzani Tizza Singabapha",
];

const TYPING_MS = 60;
const DELETING_MS = 35;
const PAUSE_MS = 1800;

export default function FooterNames() {
  const [idx, setIdx] = useState(0);
  const [text, setText] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const name = NAMES[idx];
    let timer: ReturnType<typeof setTimeout>;

    if (!deleting && text === name) {
      timer = setTimeout(() => setDeleting(true), PAUSE_MS);
    } else if (deleting && text === "") {
      setDeleting(false);
      setIdx((i) => (i + 1) % NAMES.length);
    } else {
      timer = setTimeout(
        () =>
          setText(
            deleting
              ? name.slice(0, text.length - 1)
              : name.slice(0, text.length + 1)
          ),
        deleting ? DELETING_MS : TYPING_MS
      );
    }

    return () => clearTimeout(timer);
  }, [text, deleting, idx]);

  return (
    <div className="footer-credits-inner">
      <span className="footer-credits-label">Inspired by many · </span>
      <span className="footer-name-cycle">
        {text}
        <span className="footer-name-cursor" />
      </span>
    </div>
  );
}
