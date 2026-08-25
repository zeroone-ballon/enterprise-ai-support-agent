"use client";

import { FormEvent, useState } from "react";

type SourceMode = "local" | "pdi";

const DEMO_CASES = {
  vpn: {
    label: "VPN account locked",
    short_description: "VPN account locked after repeated sign-in attempts",
    description:
      "The remote employee receives an account locked message after entering an old password several times in the corporate VPN client.",
    category: "access",
    priority: "P3",
  },
  microsoft: {
    label: "Microsoft 365 sign-in loop",
    short_description: "Microsoft 365 sign-in loops back to the login page",
    description:
      "The user can enter credentials but Outlook on the web returns to the sign-in page. The account is not reported as locked and MFA succeeds.",
    category: "access",
    priority: "P3",
  },
  disk: {
    label: "Managed PC low disk space",
    short_description: "Managed laptop reports critically low disk space",
    description:
      "The Windows laptop has less than 2 GB free on drive C. The user needs a safe cleanup procedure that does not remove business documents.",
    category: "hardware",
    priority: "P3",
  },
} as const;

type DemoCase = keyof typeof DEMO_CASES;

type Evidence = {
  knowledge_id: string;
  title: string;
  score: number;
  matched_terms: string[];
  status: string;
  updated_at: string;
};

type AssistResponse = {
  recommendation_id: string;
  incident_id: string;
  classification: { category: string; priority: string; source: string };
  recommendation: {
    status: "recommended" | "abstained";
    summary: string;
    suggested_response: string | null;
    next_actions: string[];
  };
  evidence: Evidence[];
  evaluation: {
    grounded: boolean;
    knowledge_fresh: boolean;
    sufficient_context: boolean;
    high_risk_action: boolean;
    violations: string[];
  };
  confidence: number;
  approval: { status: string; required: boolean };
  generation: { mode: string; provider: string; fallback_used: boolean };
};

function Metric({ label, value }: { label: string; value: boolean }) {
  return (
    <div className="metric">
      <span className={value ? "signal pass" : "signal fail"} aria-hidden="true" />
      <span>{label}</span>
      <strong>{value ? "Pass" : "Fail"}</strong>
    </div>
  );
}

export default function ReviewConsole() {
  const [sourceMode, setSourceMode] = useState<SourceMode>("local");
  const [demoCase, setDemoCase] = useState<DemoCase>("vpn");
  const [incidentNumber, setIncidentNumber] = useState("");
  const [result, setResult] = useState<AssistResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = incidentNumber.trim().toUpperCase();
    if (sourceMode === "pdi" && !normalized) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const demo = DEMO_CASES[demoCase];
      const response =
        sourceMode === "local"
          ? await fetch("/api/assist/local", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                incident_id: `INC-UI-${demoCase.toUpperCase()}-${Date.now()}`,
                short_description: demo.short_description,
                description: demo.description,
                category: demo.category,
                priority: demo.priority,
              }),
            })
          : await fetch(`/api/assist/servicenow/${encodeURIComponent(normalized)}`, {
              method: "POST",
            });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "Unable to review this Incident.");
      setResult(body);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unexpected console error.");
    } finally {
      setLoading(false);
    }
  }

  const recommended = result?.recommendation.status === "recommended";

  return (
    <main>
      <header className="topbar">
        <div className="brand">
          <span className="brandMark">EA</span>
          <div><strong>Enterprise AI Support</strong><span>Review Console</span></div>
        </div>
        <span className="environment"><i />Human approval required</span>
      </header>

      <section className="workspace">
        <div className="intro">
          <div><p className="eyebrow">INCIDENT REVIEW</p><h1>Ground decisions in evidence.</h1></div>
          <p>Load a local demo case or a ServiceNow PDI Incident, then inspect the recommendation and verify its retrieved evidence.</p>
        </div>

        <form className="searchPanel" onSubmit={submit}>
          <fieldset className="sourceToggle">
            <legend>Incident source</legend>
            <button type="button" className={sourceMode === "local" ? "active" : ""} onClick={() => { setSourceMode("local"); setError(""); setResult(null); }}>Local Demo</button>
            <button type="button" className={sourceMode === "pdi" ? "active" : ""} onClick={() => { setSourceMode("pdi"); setError(""); setResult(null); }}>ServiceNow PDI</button>
          </fieldset>
          <label htmlFor={sourceMode === "local" ? "demo-case" : "incident"}>{sourceMode === "local" ? "Fictional support case" : "ServiceNow Incident number"}</label>
          <div className="searchRow">
            {sourceMode === "local" ? (
              <select id="demo-case" value={demoCase} onChange={(event) => setDemoCase(event.target.value as DemoCase)}>
                {Object.entries(DEMO_CASES).map(([key, item]) => <option key={key} value={key}>{item.label}</option>)}
              </select>
            ) : (
              <input id="incident" value={incidentNumber} onChange={(event) => setIncidentNumber(event.target.value)} placeholder="INC0010002" pattern="[A-Za-z0-9._-]{1,64}" autoComplete="off" />
            )}
            <button type="submit" disabled={loading || (sourceMode === "pdi" && !incidentNumber.trim())}>{loading ? "Loading…" : "Load Incident"}</button>
          </div>
          <small>{sourceMode === "local" ? "Runs entirely against local fixtures and sandbox state. No PDI is required." : "Read-only PDI intake. Loading an Incident does not update ServiceNow."}</small>
        </form>

        {error && <div className="errorPanel" role="alert"><strong>Review unavailable</strong><span>{error}</span></div>}

        {!result && !error && !loading && (
          <div className="emptyState">
            <span className="emptyIcon">↳</span>
            <div><strong>No Incident loaded</strong><p>Enter a fictional PDI Incident number to begin an evidence review.</p></div>
          </div>
        )}

        {result && (
          <div className="reviewGrid">
            <div className="modeBanner"><span>Incident Source <strong>{sourceMode === "local" ? "Local fixture" : "ServiceNow PDI"}</strong></span><span>Execution Mode <strong>Review only</strong></span><span>External Side Effects <strong>None</strong></span></div>
            <section className="card recommendationCard">
              <div className="cardHeader">
                <div><p className="eyebrow">{result.incident_id}</p><h2>{result.recommendation.summary}</h2></div>
                <span className={`status ${recommended ? "recommended" : "abstained"}`}>{result.recommendation.status}</span>
              </div>
              <div className="metadata">
                <span>Category <strong>{result.classification.category}</strong></span>
                <span>Priority <strong>{result.classification.priority}</strong></span>
                <span>Confidence <strong>{Math.round(result.confidence * 100)}%</strong></span>
                <span>Approval <strong>{result.approval.status.replaceAll("_", " ")}</strong></span>
              </div>
              <div className="responseText">
                <p className="sectionLabel">PROPOSED RESPONSE</p>
                <p>{result.recommendation.suggested_response ?? "No response was proposed because sufficient evidence was not found."}</p>
              </div>
              <div className="guardrail">No external action is available in this read-only review stage.</div>
            </section>

            <aside className="card evaluationCard">
              <p className="sectionLabel">EVALUATION</p>
              <Metric label="Grounded" value={result.evaluation.grounded} />
              <Metric label="Knowledge fresh" value={result.evaluation.knowledge_fresh} />
              <Metric label="Context sufficient" value={result.evaluation.sufficient_context} />
              <Metric label="No high-risk action" value={!result.evaluation.high_risk_action} />
              <div className="generation">Generated by <strong>{result.generation.provider}</strong><span>{result.generation.fallback_used ? "Fallback used" : "No fallback"}</span></div>
            </aside>

            <section className="card evidenceCard">
              <div className="cardHeader"><div><p className="sectionLabel">RETRIEVED EVIDENCE</p><h2>{result.evidence.length} published candidates</h2></div></div>
              {result.evidence.length === 0 ? <p className="noEvidence">No eligible evidence cleared the relevance threshold.</p> : (
                <ol className="evidenceList">
                  {result.evidence.map((item, index) => (
                    <li key={item.knowledge_id}>
                      <span className="rank">{index + 1}</span>
                      <div className="evidenceBody"><div><strong>{item.title}</strong><code>{item.knowledge_id}</code></div><p>{item.matched_terms.join(" · ")}</p><small>Updated {item.updated_at} · {item.status}</small></div>
                      <span className="score">{Math.round(item.score * 100)}%</span>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </div>
        )}
      </section>
    </main>
  );
}
