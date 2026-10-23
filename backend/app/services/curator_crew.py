from __future__ import annotations

from fastapi import HTTPException, status
from openai import OpenAI

from app.config import settings

COUNCIL_NAMES = ["Curatorial Intelligence", "Rights & Provenance", "Market Strategy"]


def _brief(title: str, description: str, commercial_goal: str) -> str:
    return f"Artwork: {title}\nDescription and process: {description}\nIntended goal: {commercial_goal}"


def _run_native_council(title: str, description: str, commercial_goal: str) -> dict[str, object]:
    """Reliable local fallback when the optional CrewAI runtime is unavailable."""
    if not settings.openai_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Art Council AI is not configured.")
    client = OpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)
    brief = _brief(title, description, commercial_goal)
    specialist_prompts = [
        "Act as a senior contemporary-art curator. Assess artistic proposition, visual coherence, distinctiveness, material logic, context, and concrete revision opportunities. Do not invent facts.",
        "Act as an art rights and provenance reviewer. Separate supplied facts from assertions, identify missing source/rights/edition/provenance evidence, and recommend disclosures. Never offer legal certainty or authenticate the work.",
        "Act as a responsible primary-market strategist. Recommend audience, release format, edition logic, price-research method, collector narrative, and readiness gates. Never promise returns or invent comparables.",
    ]
    findings: list[str] = []
    for instruction in specialist_prompts:
        response = client.responses.create(
            model=settings.crew_model,
            instructions=instruction,
            input=brief,
        )
        findings.append(response.output_text.strip())

    synthesis = client.responses.create(
        model=settings.crew_model,
        instructions=(
            "You are the chief editor of a professional artwork review council. Synthesize the three specialist findings into a concise dossier with exactly these headings: EXECUTIVE VERDICT, CURATORIAL ASSESSMENT, AUTHORSHIP RIGHTS & PROVENANCE, MARKET & RELEASE STRATEGY, MISSING EVIDENCE, NEXT FIVE ACTIONS. "
            "Clearly distinguish known facts, missing evidence, and recommendations. Never claim authenticity, legal clearance, valuation certainty, or investment performance. Use plain text and short paragraphs."
        ),
        input=f"{brief}\n\nCURATOR FINDINGS\n{findings[0]}\n\nRIGHTS FINDINGS\n{findings[1]}\n\nMARKET FINDINGS\n{findings[2]}",
    )
    return {"report": synthesis.output_text.strip(), "engine": "Vernis native agent council", "agents": COUNCIL_NAMES}


def run_art_advisory(title: str, description: str, commercial_goal: str) -> dict[str, object]:
    """Run the optional curator/provenance/market advisory crew.

    CrewAI is intentionally isolated from the image generation path: advisory
    can fail or be disabled without interrupting artwork production.
    """
    if not settings.crew_enabled:
        return _run_native_council(title, description, commercial_goal)
    try:
        from crewai import Agent, Crew, Process, Task
    except ImportError:
        return _run_native_council(title, description, commercial_goal)

    curator = Agent(
        role="Senior art curator",
        goal="Evaluate artistic coherence, distinctiveness, and exhibition context without inventing provenance.",
        backstory="You advise galleries and artists with disciplined visual analysis.",
        llm=settings.crew_model,
        verbose=False,
    )
    rights_specialist = Agent(
        role="Art rights and provenance reviewer",
        goal="Flag rights, attribution, provenance, edition, and disclosure gaps; never claim legal certainty.",
        backstory="You build auditable artwork records and identify questions for qualified counsel.",
        llm=settings.crew_model,
        verbose=False,
    )
    market_advisor = Agent(
        role="Art market strategist",
        goal="Recommend positioning, edition structure, pricing evidence, and sale format without guaranteeing returns.",
        backstory="You advise responsible primary-market releases and collector communication.",
        llm=settings.crew_model,
        verbose=False,
    )
    chief_editor = Agent(
        role="Chief artwork dossier editor",
        goal="Synthesize specialist findings into a precise, evidence-aware dossier for a human approval decision.",
        backstory="You edit institutional artwork records and never turn uncertain evidence into a claim.",
        llm=settings.crew_model,
        verbose=False,
    )
    brief = _brief(title, description, commercial_goal)
    curator_task = Task(description=f"Assess the artistic proposition and curatorial context.\n{brief}", expected_output="Curatorial strengths, weaknesses, context, and revision opportunities.", agent=curator)
    rights_task = Task(description=f"Audit the supplied facts for rights and provenance gaps.\n{brief}", expected_output="A checklist separating known facts, missing evidence, risks, and recommended disclosures.", agent=rights_specialist)
    market_task = Task(description=f"Develop a responsible market and release recommendation.\n{brief}", expected_output="Audience, sale format, edition logic, price research plan, readiness gates, and collector narrative.", agent=market_advisor)
    dossier_task = Task(
        description="Synthesize every specialist finding. Use headings: EXECUTIVE VERDICT, CURATORIAL ASSESSMENT, AUTHORSHIP RIGHTS & PROVENANCE, MARKET & RELEASE STRATEGY, MISSING EVIDENCE, NEXT FIVE ACTIONS. Never claim authenticity, legal clearance, valuation certainty, or investment returns.",
        expected_output="A concise professional artwork dossier with explicit facts, gaps, recommendations, and five next actions.",
        agent=chief_editor,
        context=[curator_task, rights_task, market_task],
    )
    crew = Crew(agents=[curator, rights_specialist, market_advisor, chief_editor], tasks=[curator_task, rights_task, market_task, dossier_task], process=Process.sequential, verbose=False)
    try:
        result = str(crew.kickoff())
        return {"report": result, "engine": "CrewAI multi-agent council", "agents": COUNCIL_NAMES}
    except Exception:
        return _run_native_council(title, description, commercial_goal)
