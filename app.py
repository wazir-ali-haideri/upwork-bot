"""
Upwork Proposal Bot — Wazir Ali H.  ·  Ultimate Edition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Features:
  • Multi-model consensus  (Mistral Large + Groq/Llama + fallback chain)
  • Chairman synthesis     (best of all drafts, 99.9% client-aligned)
  • Live web research      (DuckDuckGo — real industry context)
  • KPI gate               (9 quality flags before spending Connects)
  • Privacy pledge section (GDPR-style client data assurance)
  • Pilot / test-task offer
  • Meeting availability CTA
  • Client chat assistant
"""

import streamlit as st
import json, re
import PyPDF2
import io

# Custom Modules
def extract_pdf_text(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t: text += t + "\n"
        return text
    except Exception:
        return ""

from ui.styles import CSS_STYLES
from data.profile import PROFILE, BASE_SYSTEM
from api.llms import call_mistral, call_with_fallback, chairman_synthesis
from api.search import build_research_context
from core.kpi import frow, calc_score, verdict

# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Upwork Proposal Writer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CSS_STYLES, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 👤 Your Profile")
    st.markdown("---")
    
    cv_file = st.file_uploader("Upload CV or Profile (.pdf)", type=["pdf"])
    manual_profile = st.text_area("Or paste your skills manually:", height=100)
    
    active_profile = PROFILE
    if cv_file:
        active_profile = extract_pdf_text(cv_file)
    elif manual_profile.strip():
        active_profile = manual_profile
        
    st.session_state["active_profile"] = active_profile

    # API Keys securely managed backend
    mistral_key = st.secrets.get("MISTRAL_API_KEY", "")
    groq_key = st.secrets.get("GROQ_API_KEY", "")
    gemini_key = st.secrets.get("GEMINI_API_KEY", "")

    st.markdown("---")
    st.markdown("### 📝 Proposal Settings")
    length = st.selectbox("Length",
        ["Concise (130–170 words)","Standard (190–260 words)","Detailed (280–370 words)"],
        index=1)
    project_type = st.selectbox("Project type",
        ["Auto-detect","Data annotation / labeling","CV / object detection",
         "ML model training / deployment","NLP / LLM","Data analysis / BI",
         "Full AI pipeline","Reinforcement learning"])
    extra_ctx = st.text_area("Extra context (optional)",
        placeholder="Any specific detail to emphasise — similar past project, tool, deadline...",
        height=70)
    do_research = st.checkbox("🌐 Enable web research (DuckDuckGo)", value=True,
        help="Searches the web for industry context to enrich the proposal")

    st.markdown("---")
    st.markdown("### 🚩 KPI Thresholds")
    min_hr     = st.slider("Min hiring rate (%)",    60, 100, 86)
    max_posted = st.slider("Max posted (min ago)",    5,  60, 20)
    max_props  = st.slider("Max proposals on job",    1,  20,  4)
    max_interv = st.slider("Max interviewing",        0,  10,  2)
    max_inv    = st.slider("Max invites sent",        0,  10,  2)
    max_unan   = st.slider("Max unanswered invites",  0,  10,  2)
    min_rat    = st.slider("Min client rating ★",    3.0, 5.0, 4.8, step=0.1)

    st.markdown("---")
    st.markdown('<div style="font-size:11px;color:#1e2a4a;line-height:1.7">'
                'Upwork Proposal Writer<br>'
                'Advanced AI Synthesis<br>'
                'IMPACT Framework · IMPACT Framework</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hdr">
  <h1>🎯 Upwork Proposal Writer</h1>
  <p>Advanced AI Synthesis · Web research · KPI gating · Privacy pledge · Pilot offer</p>
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# JOB INPUT
# ─────────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">📋 Paste the full Upwork job post</div>', unsafe_allow_html=True)
job_desc = st.text_area("jd", height=220, label_visibility="collapsed",
    placeholder=(
        "Paste EVERYTHING you can see on the job page:\n"
        "— Job title + full description\n"
        "— Budget, timeline\n"
        "— Client stats: hiring rate, rating, location, payment verified\n"
        "— Activity: Proposals: Less than 5 / Interviewing: 1 / Invites sent: 2\n\n"
        "The more you paste, the better the KPI check AND the proposal."
    ))
st.markdown(f'<div style="font-size:11px;color:#151525;text-align:right">{len(job_desc)} chars</div>',
            unsafe_allow_html=True)

c1, c2 = st.columns([3, 1])
with c1:
    go_btn    = st.button("🚀  Analyze KPIs + Research + Generate Proposal", use_container_width=True)
with c2:
    force_btn = st.button("⚡  Force Write Anyway", use_container_width=True)

# ─────────────────────────────────────────────────────────────────
# MAIN FLOW
# ─────────────────────────────────────────────────────────────────
if go_btn or force_btn:
    if not job_desc.strip():
        st.warning("⚠️ Paste a job description first."); st.stop()
    if not mistral_key:
        st.error("❌ Add your Mistral key in the sidebar."); st.stop()

    # ── 1. EXTRACT KPIs ──────────────────────────────────────────
    with st.spinner("🔍 Extracting job KPIs..."):
        try:
            kpi_prompt = f"""Extract job metrics. Return ONLY valid JSON — no markdown, no fences.
{{"hiring_rate":int,"client_rating":float,"posted_minutes":int,
  "payment_verified":"Verified"|"Not verified"|"Unknown",
  "proposals_count":int,"invites_sent":int,"interviewing_count":int,
  "unanswered_invites":int,"client_country":string}}
Rules: hours→minutes; "less than 5"→4; 0/"" if not found.
TEXT: {job_desc}"""
            raw_kpi, _ = call_mistral(mistral_key,
                "Return only raw JSON. No explanations.", kpi_prompt,
                model="mistral-small-latest")
            clean = re.sub(r"```(?:json)?","",raw_kpi).replace("```","").strip()
            m = re.search(r'\{.*\}', clean, re.DOTALL)
            if m: clean = m.group(0)
            d = json.loads(clean)
            si = lambda v: max(0, int(v)) if v else 0
            sf = lambda v: max(0.0, float(v)) if v else 0.0
            ss = lambda v: str(v).strip() if v else ""
            kpi = dict(
                hr=si(d.get("hiring_rate")), cr=sf(d.get("client_rating")),
                pm=si(d.get("posted_minutes")), pc=si(d.get("proposals_count")),
                inv=si(d.get("invites_sent")), intv=si(d.get("interviewing_count")),
                unan=si(d.get("unanswered_invites")), ctry=ss(d.get("client_country")),
                pv=ss(d.get("payment_verified","Unknown")),
            )
        except Exception as e:
            st.error(f"KPI extraction failed: {e}"); st.stop()

    # ── 2. EVALUATE FLAGS ─────────────────────────────────────────
    flags = {}
    rows  = ""
    def fr(k, p, lbl, val, note=""):
        flags[k] = p
        return frow("✅" if p else "⚠️", lbl, val, "p" if p else "f", note)

    rows += fr("hr",     kpi["hr"]   >= min_hr,     f"Hiring rate (≥{min_hr}%)",      f"{kpi['hr']}%")
    rows += fr("rating", kpi["cr"]   >= min_rat,    f"Client rating (≥{min_rat:.1f}★)",f"{kpi['cr']:.1f}★")
    rows += fr("posted", kpi["pm"]   <= max_posted, f"Posted (≤{max_posted} min)",    f"{kpi['pm']} min" if kpi['pm'] else "Just now 🔥")
    rows += fr("props",  kpi["pc"]   <= max_props,  f"Proposals (≤{max_props})",      str(kpi["pc"]), "🎯 low!" if kpi["pc"] <= 2 else "")
    rows += fr("interv", kpi["intv"] <= max_interv, f"Interviewing (≤{max_interv})",  str(kpi["intv"]))
    rows += fr("inv",    kpi["inv"]  <= max_inv,    f"Invites sent (≤{max_inv})",     str(kpi["inv"]))
    rows += fr("unan",   kpi["unan"] <= max_unan,   f"Unanswered (≤{max_unan})",      str(kpi["unan"]))

    pay_crit = "verif" not in kpi["pv"].lower() or "not" in kpi["pv"].lower()
    flags["pay"] = not pay_crit
    rows += frow("🚫" if pay_crit else "✅", "Payment [CRITICAL]", kpi["pv"],
                 "f" if pay_crit else "p")

    blocked = ["pakistan","india"]
    ctry_crit = any(b in kpi["ctry"].lower() for b in blocked) if kpi["ctry"] else False
    flags["ctry"] = not ctry_crit
    rows += frow("🚫" if ctry_crit else "✅", "Country [CRITICAL]",
                 kpi["ctry"] or "Unknown", "f" if ctry_crit else "p",
                 "⛔ Blocked" if ctry_crit else "")

    crit = pay_crit or ctry_crit
    score = calc_score(flags)
    if crit: score = min(score, 15)
    vtype, vtxt, vsub = verdict(score, crit)
    failed = [k for k,v in flags.items() if v is False]

    st.session_state.update(dict(
        rows=rows, score=score, vtype=vtype, vtxt=vtxt, vsub=vsub,
        failed=failed, crit=crit, force=force_btn, kpi=kpi, job=job_desc,
    ))

    should_gen = force_btn or not failed

    if should_gen:
        len_map = {"Concise (130–170 words)":"130–170 words",
                   "Standard (190–260 words)":"190–260 words",
                   "Detailed (280–370 words)":"280–370 words"}

        # ── 3. WEB RESEARCH ──────────────────────────────────────
        research_ctx = ""
        raw_results  = []
        if do_research:
            with st.spinner("🌐 Searching web for industry context..."):
                research_ctx, raw_results = build_research_context(job_desc, mistral_key)
        st.session_state["research_ctx"]  = research_ctx
        st.session_state["raw_results"]   = raw_results

        # ── 4. PARALLEL MODEL DRAFTS ─────────────────────────────
        draft_prompt = f"""Write a winning Upwork proposal for this job.

JOB:
{job_desc}

JOB CONTEXT:
• Posted {kpi['pm']} min ago {'— apply immediately!' if kpi['pm'] <= 10 else ''}
• {kpi['pc']} proposals so far {'— low competition!' if kpi['pc'] <= 3 else '— be specific'}
• Client hiring rate: {kpi['hr']}%
• Country: {kpi['ctry'] or 'Unknown'}
{f'• EXTRA CONTEXT: {extra_ctx}' if extra_ctx else ''}
{'• WEB RESEARCH INSIGHTS: ' + research_ctx[:600] if research_ctx else ''}

REQUIREMENTS:
• Length: {len_map.get(length,'190–260 words')}
• Project type: {project_type}
• Include meeting offer + pilot task offer + data privacy line naturally
• Use ONLY real proof points from the profile — never invent stats
• If large-scale or time-sensitive → mention 7-person team

Write ONLY the proposal text. No labels. No "Here is the proposal:".

FREELANCER PROFILE:
{st.session_state.get("active_profile", "")}"""

        with st.spinner("⚡ Running AI engines in parallel..."):
            drafts = call_with_fallback(BASE_SYSTEM, draft_prompt, mistral_key, groq_key, gemini_key)
        st.session_state["drafts"] = drafts

        # ── 5. CHAIRMAN SYNTHESIS ────────────────────────────────
        with st.spinner("👑 Final AI synthesising proposal..."):
            final = chairman_synthesis(mistral_key, job_desc, drafts,
                                       research_ctx, st.session_state.get("active_profile", PROFILE), BASE_SYSTEM)
        st.session_state["final"] = final
        st.session_state["chat_history"] = []

    st.rerun()

# ─────────────────────────────────────────────────────────────────
# RENDER PERSISTED RESULTS
# ─────────────────────────────────────────────────────────────────
if "rows" not in st.session_state:
    st.stop()

left, right = st.columns([1, 1.15], gap="large")

# ── KPI PANEL ────────────────────────────────────────────────────
with left:
    st.markdown('<div class="sec-title">🚩 Job Quality Flags</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kpi-panel"><h4>KPI Check</h4>{st.session_state["rows"]}</div>',
                unsafe_allow_html=True)

    sc  = st.session_state["score"]
    scl = "sg" if sc >= 75 else ("sy" if sc >= 50 else "sr")
    st.markdown(f'<div class="scring {scl}"><div class="scn">{sc}</div>'
                f'<div class="scl">/ 100 — Job Quality</div></div>', unsafe_allow_html=True)

    vc = {"go":"vgo","maybe":"vmy","skip":"vsk"}[st.session_state["vtype"]]
    st.markdown(f'<div class="{vc}"><p>{st.session_state["vtxt"]}</p>'
                f'<div style="font-size:11px;color:#444;margin-top:3px">'
                f'{st.session_state["vsub"]}</div></div>', unsafe_allow_html=True)

    fk = st.session_state.get("failed",[])
    if fk:
        st.markdown(f'<div class="warn">⚠️ Failed: {" · ".join(fk)}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ok">✅ All flags passed — great opportunity!</div>', unsafe_allow_html=True)

# ── RIGHT: WEB RESEARCH PREVIEW ──────────────────────────────────
with right:
    rr = st.session_state.get("raw_results",[])
    if rr:
        st.markdown('<div class="sec-title">🌐 Web Research Used</div>', unsafe_allow_html=True)
        for r in rr[:3]:
            st.markdown(
                f'<div class="research-card"><div class="rt">🔗 {r["title"]}</div>{r["snippet"]}</div>',
                unsafe_allow_html=True)
    elif st.session_state.get("vtype") == "skip" and not st.session_state.get("force"):
        st.markdown("""
        <div style="background:#100404;border:2px solid #c03030;border-radius:12px;
                    padding:22px;text-align:center;margin-top:20px">
          <div style="font-size:28px;margin-bottom:8px">⛔</div>
          <div style="color:#d05050;font-size:15px;font-weight:700">Generation blocked</div>
          <div style="color:#603030;font-size:12px;margin-top:6px">
            Failed KPI checks. Use Force Write to override.</div>
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# OUTPUT TABS
# ─────────────────────────────────────────────────────────────────
if "final" not in st.session_state:
    if fk and not st.session_state.get("force"):
        st.markdown('<div class="warn" style="margin-top:12px">⛔ Generation blocked — job failed KPI checks. Click "Force Write Anyway" to override.</div>',
                    unsafe_allow_html=True)
    st.stop()

st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs([
    "✍️  Final Proposal",
    "🤖  Model Drafts",
    "💡  Win Strategy",
    "💬  Chat Assistant",
])

final_text = st.session_state["final"]

# ══════════════════════════════════════════════════════════════════
# TAB 1 — FINAL CHAIRMAN PROPOSAL
# ══════════════════════════════════════════════════════════════════
with tab1:
    wc = len(final_text.split())
    st.markdown(
        f'<div class="final-wrap">'
        f'<div class="wc-badge">{wc} words</div>'
        f'<div class="prop-text">{final_text}</div>'
        f'</div>', unsafe_allow_html=True)

    # Privacy badge
    st.markdown("""
    <div class="privacy-badge">
      <div class="pt">🔒 Data Privacy Assurance (included in proposal)</div>
      Your client's data, code, and project details are fully confidential —
      never shared with third parties, never used outside this project.
      Wazir operates under strict data minimization principles aligned with GDPR Article 5,
      with secure file handling and no external AI training on client work product.
    </div>""", unsafe_allow_html=True)

    ca, cb, cc = st.columns(3)
    with ca:
        if st.button("📋 Copyable text"):
            st.code(final_text, language=None)
    with cb:
        if st.button("✂️ Make shorter"):
            with st.spinner("Shortening..."):
                s, _ = call_mistral(mistral_key, BASE_SYSTEM,
                    f"Cut 25%. Keep hook, proof, pilot+meeting offer, privacy line, closing question. "
                    f"Remove filler only.\n\nPROPOSAL:\n{final_text}\n\nReturn ONLY the shortened proposal.")
                st.session_state["final"] = s; st.rerun()
    with cc:
        if st.button("🔄 Fresh rewrite"):
            with st.spinner("Rewriting..."):
                r, _ = call_mistral(mistral_key, BASE_SYSTEM,
                    f"Rewrite with a completely different opening hook and angle.\n"
                    f"Same job, same rules, fresh perspective.\n\n"
                    f"JOB:\n{st.session_state['job']}\n\n"
                    f"Return ONLY the rewritten proposal.")
                st.session_state["final"] = r; st.rerun()

# ══════════════════════════════════════════════════════════════════
# TAB 2 — MODEL DRAFTS + CONSENSUS TRANSPARENCY
# ══════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="info">Multiple AI approaches drafted independent proposals. The Final Synthesis combined the best elements.</div>',
                unsafe_allow_html=True)

    drafts = st.session_state.get("drafts", [])

    for i, d in enumerate(drafts):
        if d.get("ok", False):
            wc2 = len(d["text"].split())
            badge = f'<span class="model-score ms-high">{wc2}w</span>'
            st.markdown(
                f'<div class="model-card mc-mistral">'
                f'<div class="model-label ml-mistral">🤖 AI Draft Approach {i+1}{badge}</div>'
                f'<div class="model-text">{d["text"]}</div></div>',
                unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="model-card mc-mistral">'
                f'<div class="model-label ml-mistral">🤖 AI Draft Approach {i+1} — ❌ Failed</div>'
                f'<div class="model-text" style="color:#703030">{d.get("error", "Error")}</div></div>',
                unsafe_allow_html=True)

    # Synthesis card
    st.markdown(
        f'<div class="model-card mc-chairman" style="margin-top:24px">'
        f'<div class="model-label ml-chairman" style="margin-top:6px">'
        f'🏛️ Final Synthesis — Selected Output</div>'
        f'<div class="model-text">{final_text}</div></div>',
        unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# TAB 3 — WIN STRATEGY
# ══════════════════════════════════════════════════════════════════
with tab3:
    if "strategy" not in st.session_state:
        with st.spinner("Building win strategy..."):
            kpi = st.session_state.get("kpi",{})
            strat, _ = call_mistral(mistral_key, BASE_SYSTEM,
                f"""Write a practical job-winning strategy for this Upwork job.

JOB: {st.session_state['job']}
Score: {st.session_state['score']}/100 | Posted: {kpi.get('pm',0)} min | Proposals: {kpi.get('pc',0)} | HR: {kpi.get('hr',0)}%

Write these 5 sections — be specific to THIS job, not generic:

**🎯 What the client REALLY wants**
Beyond the job description — what is the underlying goal and fear driving this post?

**💰 Pricing strategy**
Specific bid recommendation (hourly or fixed, with range). Above / at / below budget and why.

**📎 What to attach**
Exactly which portfolio piece or sample would be most persuasive for THIS job.

**⚡ Speed & competition edge**
Based on {kpi.get('pm',0)} minutes posted and {kpi.get('pc',0)} proposals — what is the tactical window?

**🔄 Follow-up message (write it out)**
If no reply after 48 hours — the exact message to send, ready to copy-paste."""
            )
            st.session_state["strategy"] = strat

    st.markdown(f'<div class="model-card mc-mistral" style="line-height:1.85;font-size:14px;color:#a0a8d0">'
                f'{st.session_state["strategy"]}</div>', unsafe_allow_html=True)
    if st.button("🔄 Regenerate strategy"):
        del st.session_state["strategy"]; st.rerun()

# ══════════════════════════════════════════════════════════════════
# TAB 4 — CHAT ASSISTANT
# ══════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 💬 Client replied? Get your response in seconds.")
    st.markdown('<div class="info">Paste the client\'s message — the bot drafts your reply based on the job, your proposal, and your profile.</div>',
                unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    for msg in st.session_state["chat_history"]:
        role_class = "cb-client" if msg["role"] == "client" else "cb-me"
        role_label = "🏢 CLIENT" if msg["role"] == "client" else "✍️ YOUR REPLY (draft)"
        st.markdown(
            f'<div class="{role_class}"><div class="cb-label">{role_label}</div>'
            f'{msg["content"]}</div>', unsafe_allow_html=True)

    client_msg = st.text_area("Client message:", height=100, key="chat_in",
        placeholder="Paste what the client wrote to you...")

    c_send, c_clear = st.columns([3,1])
    with c_send:
        if st.button("💬 Draft my reply", use_container_width=True):
            if client_msg.strip():
                st.session_state["chat_history"].append({"role":"client","content":client_msg.strip()})
                hist = "\n".join(
                    f"{'CLIENT' if m['role']=='client' else 'WAZIR'}: {m['content']}"
                    for m in st.session_state["chat_history"])
                with st.spinner("Drafting reply..."):
                    rep, _ = call_mistral(mistral_key, BASE_SYSTEM,
                        f"""Write Wazir's reply to the client.

JOB: {st.session_state.get('job','')[:400]}
PROPOSAL: {st.session_state.get('final','')[:300]}

CONVERSATION:
{hist}

Rules:
• 2–4 sentences max. Direct and human.
• Match the client's energy level
• If they ask a question → answer it specifically
• If ready to proceed → suggest a 15-min call or ask for files
• Confident, not desperate
• End with a natural next-step

Write ONLY the reply.""")
                st.session_state["chat_history"].append({"role":"wazir","content":rep})
                st.rerun()
            else:
                st.warning("Paste the client's message first.")
    with c_clear:
        if st.button("🗑️ Clear"):
            st.session_state["chat_history"] = []; st.rerun()

# ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center;font-size:11px;color:#0e1428;padding:5px 0">'
    'Upwork Proposal Writer<br>'
                'Advanced AI Synthesis<br>'
                'IMPACT Framework · IMPACT Framework · DuckDuckGo Research</div>',
    unsafe_allow_html=True)