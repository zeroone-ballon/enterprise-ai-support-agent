"use client";

import { FormEvent, useState } from "react";

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
  const [incidentNumber, setIncidentNumber] = useState("");
  const [result, setResult] = useState<AssistResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = incidentNumber.trim().toUpperCase();
    if (!normalized) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch(`/api/assist/servicenow/${encodeURIComponent(normalized)}`, {
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
          <p>Load one ServiceNow PDI Incident, inspect the recommendation and verify every cited source before approval.</p>
        </div>

        <form className="searchPanel" onSubmit={submit}>
          <label htmlFor="incident">ServiceNow Incident number</label>
          <div className="searchRow">
            <input id="incident" value={incidentNumber} onChange={(event) => setIncidentNumber(event.target.value)} placeholder="INC0010002" pattern="[A-Za-z0-9._-]{1,64}" autoComplete="off" />
            <button type="submit" disabled={loading || !incidentNumber.trim()}>{loading ? "Loading…" : "Load Incident"}</button>
          </div>
          <small>Read-only intake. Loading an Incident does not update ServiceNow.</small>
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
              <div className="cardHeader"><div><p className="sectionLabel">CITED EVIDENCE</p><h2>{result.evidence.length} published sources</h2></div></div>
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
