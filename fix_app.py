import os

path = r"c:\Users\WazirAliHaideri\Desktop\proposal write\app.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Imports
code = code.replace("import json, re", "import json, re\nimport PyPDF2\nimport io")

# 2. Extract PDF function
code = code.replace("from ui.styles import CSS_STYLES", 
"""def extract_pdf_text(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t: text += t + "\\n"
        return text
    except Exception:
        return ""

from ui.styles import CSS_STYLES""")

# 3. Titles
code = code.replace('page_title="Proposal Bot — Wazir Ali H.",', 'page_title="Upwork Proposal Writer",')
code = code.replace('page_title="Proposal Bot — SAMEER ALI FROM WAZIR",', 'page_title="Upwork Proposal Writer",')

code = code.replace('<h1>🎯 Upwork Proposal Bot <span class="badge">Wazir Ali H.</span></h1>', '<h1>🎯 Upwork Proposal Writer</h1>')
code = code.replace('<p>Multi-model consensus · Web research · KPI gating · Privacy pledge · Pilot offer · Mistral + Groq + Gemini</p>', '<p>Advanced AI Synthesis · Web research · KPI gating · Privacy pledge · Pilot offer</p>')

# 4. Sidebar Keys -> Profile
import re

sidebar_pattern = re.compile(
    r'with st\.sidebar:(.*?)st\.markdown\("---"\)\s+st\.markdown\("### 📝 Proposal Settings"\)', 
    re.DOTALL
)

new_sidebar = """with st.sidebar:
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
    st.markdown("### 📝 Proposal Settings")"""

code = sidebar_pattern.sub(new_sidebar, code)

# 5. Small texts
code = code.replace(
    'Wazir Ali H. · ~010c1abd1a9762fe8b<br>\'\\n                \'Mistral Large + Groq LLaMA + Gemini Pro<br>\'\\n                \'Chairman Consensus', 
    'Upwork Proposal Writer<br>\'\\n                \'Advanced AI Synthesis<br>\'\\n                \'IMPACT Framework'
)

# Replace the other exact occurrences just in case:
code = re.sub(r"'Wazir Ali H\. · ~010c1abd1a9762fe8b.*?Chairman Consensus", "'Upwork Proposal Writer<br>'\\n                'Advanced AI Synthesis<br>'\\n                'IMPACT Framework", code, flags=re.DOTALL)

# 6. Draft profiles
old_draft_ending = 'Write ONLY the proposal text. No labels. No "Here is the proposal:".'
new_draft_ending = 'Write ONLY the proposal text. No labels. No "Here is the proposal:".\\n\\nFREELANCER PROFILE:\\n{st.session_state.get(\\\'active_profile\\\', \\\'\\\')}'
code = code.replace(old_draft_ending, new_draft_ending)

# 7. Chairman profile passing
code = code.replace(
    'final = chairman_synthesis(mistral_key, job_desc, drafts,\n                                       research_ctx, PROFILE, BASE_SYSTEM)',
    'final = chairman_synthesis(mistral_key, job_desc, drafts,\n                                       research_ctx, st.session_state.get("active_profile", PROFILE), BASE_SYSTEM)'
)

# 8. Texts
code = code.replace('running models in parallel (Mistral + Groq + Gemini)', 'running AI engines in parallel')
code = code.replace('Chairman synthesising final proposal', 'Final AI synthesising proposal')

# 9. Tab 2
tab2_pattern = re.compile(
    r'Each model wrote an independent draft(.*?)# ══════════════════════════════════════════════════════════════════\n# TAB 3',
    re.DOTALL | re.IGNORECASE
)

new_tab2 = """Multiple AI approaches drafted independent proposals. The Final Synthesis combined the best elements.</div>',
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
# TAB 3"""

code = tab2_pattern.sub(new_tab2, code)

# 10. Footer
code = re.sub(
    r"'Wazir Ali H\. · ~010c1abd1a9762fe8b.*?DuckDuckGo Research",
    "'Upwork Proposal Writer · Advanced AI Ensemble · '    'Synthesis Consensus · IMPACT Framework · Live Research",
    code, flags=re.DOTALL
)

with open(path, "w", encoding="utf-8") as f:
    f.write(code)
print("Done!")
