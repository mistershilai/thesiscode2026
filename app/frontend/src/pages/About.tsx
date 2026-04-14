import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Summary } from "../api/client";
import AnimatedTagline from "../components/AnimatedTagline";
import FooterNames from "../components/FooterNames";
import Signature from "../components/Signature";

export default function About() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [drugCount, setDrugCount] = useState<number>(0);

  useEffect(() => {
    api.getSummary().then(setSummary).catch(console.error);
    api.getCmsProducts().then((p) => setDrugCount(p.length)).catch(console.error);
  }, []);

  const fac = summary?.total_facilities ?? "...";
  const pop = summary ? (summary.total_population / 1e6).toFixed(1) + "M" : "...";
  const dhmts = summary?.dhmt_count ?? "...";
  const drugs = drugCount || "...";

  return (
    <div className="page about-page">
      <div className="about-hero">
        <h1 className="about-title">Kaelo</h1>
        <p className="about-meaning">
          /ka.ˈe.lo/ · <em>Setswana</em> · "to care for, to nurture, to look after"
        </p>
        <div className="about-divider" />
        <p className="about-mission">
          When a child in rural Botswana needs antibiotics, the distance between
          life and loss is measured not in kilometers, but in whether the right
          medicine sits on the right shelf at the right moment.
        </p>
        <p className="about-mission">
          Kaelo exists to close that gap.
        </p>
      </div>

      <div className="about-section">
        <h2>What We Do</h2>
        <p>
          Kaelo is an antimicrobial supply chain optimization platform built for the
          Government of Botswana. It uses advanced mathematical models, including robust optimization
          and adaptive decision rules, to determine how medicines should be procured,
          stored, and distributed across the country's {fac} health facilities.
        </p>
        <p>
          The system accounts for demand uncertainty, transport constraints, procurement costs,
          and the complex tiered network of warehouses, hospitals, clinics, and health posts
          that serve {pop} people across {dhmts} health districts.
        </p>
      </div>

      <div className="about-section">
        <h2>Why It Matters</h2>
        <div className="about-stats-row">
          <div className="about-stat">
            <div className="about-stat-value">{fac}</div>
            <div className="about-stat-label">Health facilities served</div>
          </div>
          <div className="about-stat">
            <div className="about-stat-value">{pop}</div>
            <div className="about-stat-label">People across Botswana</div>
          </div>
          <div className="about-stat">
            <div className="about-stat-value">{drugs}</div>
            <div className="about-stat-label">Antimicrobial products optimized</div>
          </div>
          <div className="about-stat">
            <div className="about-stat-value">{dhmts}</div>
            <div className="about-stat-label">DHMT health districts</div>
          </div>
        </div>
        <p>
          Antimicrobial resistance is one of the greatest threats to global health.
          Ensuring the right antibiotics reach the right patients, no more, no less,
          is critical to both saving lives today and preserving these medicines for tomorrow.
        </p>
      </div>

      <div className="about-section">
        <h2>How It Works</h2>
        <div className="about-steps">
          <div className="about-step">
            <div className="about-step-num">01</div>
            <div>
              <h3>Model</h3>
              <p>
                Demand is derived from CMS national procurement records, distributed
                across facilities based on census population shares.
              </p>
            </div>
          </div>
          <div className="about-step">
            <div className="about-step-num">02</div>
            <div>
              <h3>Optimize</h3>
              <p>
                Three strategies (Nominal, Static Robust, and Adjustable Robust)
                solve for procurement and distribution plans that balance cost, coverage,
                and resilience to demand uncertainty.
              </p>
            </div>
          </div>
          <div className="about-step">
            <div className="about-step-num">03</div>
            <div>
              <h3>Plan</h3>
              <p>
                District pharmacists input current inventory, and the system generates
                specific shipment orders: what to buy, where to send it, and how much,
                computed using real road distances from OSRM routing.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="about-section">
        <h2>Built With Purpose</h2>
        <p>
          Kaelo was born during the 2025 medical crisis in Botswana, when supply chain
          disruptions exposed the fragility of antimicrobial distribution across the country.
          What began as a senior thesis at Princeton University's Department of Operations
          Research and Financial Engineering (ORFE) became something more urgent: a direct
          response to a system under strain.
        </p>
        <p>
          Built in collaboration with ACHAP, the Ministry of Health of Botswana, and the
          Central Medical Stores, Kaelo was never meant to be an academic exercise. It was
          built as a tool for the people who wake up every day to keep Botswana's health
          system running.
        </p>
        <p className="about-tswana">
          Ke a leboga, Botswana. Pelo ya me e tletse tebogo. Pula.
        </p>
      </div>

      <div className="about-section about-people">
        <h2>The People Behind Kaelo</h2>
        <div className="about-credits-grid">
          <div className="about-credit-group">
            <h4>Research &amp; Development</h4>
            <p>Elliot Lee · Lead Researcher &amp; Developer</p>
            <p>Bartolomeo Stellato · Faculty Advisor</p>
            <p>Stefan Clarke · Graduate TA</p>
          </div>
          <div className="about-credit-group">
            <h4>Global Health Program</h4>
            <p>Gilbert Collins</p>
            <p>Hanna Ehrlich</p>
          </div>
          <div className="about-credit-group">
            <h4>ACHAP Partners</h4>
            <p>Khumo Seipone</p>
            <p>Lesego Busang</p>
            <p>Kabelo Kgongwana</p>
            <p>Stanley Mapiki</p>
            <p>Tiro Molefe</p>
            <p>Blessed Monyatsi</p>
          </div>
          <div className="about-credit-group">
            <h4>Regional Partners (ACHAP)</h4>
            <p className="about-credit-note">Medical professionals and ACHAP-affiliated health workers</p>
            <p>Boseki Gaipone · Palapye</p>
            <p>Atang Motlogelwa · Bobonong</p>
            <p>Ofentse Seosenyeng · Mahalapye</p>
          </div>
          <div className="about-credit-group">
            <h4>Ministry of Health &amp; CMS</h4>
            <p>Bene D. Anand Paramadhas</p>
            <p>Seadingwane Kgotlele</p>
            <p>Tseleng Selabe</p>
            <p>Gaotlhalefshe Mosa Gaolekwe</p>
            <p>Celda Tirayakgosi</p>
            <p>Idah Seepo</p>
            <p>Teedzani Tizza Singabapha</p>
          </div>
        </div>
        <div className="about-signature-area">
          <Signature />
        </div>
      </div>

      <div className="about-closing">
        <p className="about-closing-text">
          May the spirit of generosity, resilience, and shared purpose that defines
          Botswana continue to inspire this work and all those who contribute to it.
        </p>
        <p className="about-pula">Pula.</p>
      </div>
    </div>
  );
}
