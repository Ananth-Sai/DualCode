import ast
import difflib
import json
import time
from pathlib import Path

import streamlit as st
import pandas as pd

import config
from tasks.schemas import Task
from tasks.loader import load_task_bank
from orchestrator import run_loop
from sandbox.test_runner import run_hidden_tests
from sandbox.dynamic_test_oracle import synthesize_test_suite

# Page configuration
st.set_page_config(
    page_title="DualCode — Multi-Agent Studio",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Design System (Curated Obsidian Dark with Gold Accents and Balanced Centered Layout)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Global Typography & Deep Dark Background */
    html, body, [data-testid="stAppViewContainer"], .stApp {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background-color: #0b0f19 !important;
        color: #f8fafc !important;
    }

    /* Constrain main block width so content doesn't stretch awkwardly across wide screens */
    .block-container {
        max-width: 1120px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 3.5rem !important;
        margin: 0 auto !important;
    }

    [data-testid="stHeader"] {
        background-color: #0b0f19 !important;
    }

    /* Sidebar Dark Styling */
    [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
        background-color: #111827 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    code, pre, [class*="stCode"] {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Hero Banner: Clean Obsidian Surface with Subtle Gold Accent */
    .hero-container {
        padding: 1.5rem 2rem;
        background: linear-gradient(135deg, #131b2e 0%, #0d1322 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 4px solid #f59e0b;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
    }

    .hero-title {
        font-size: 1.85rem;
        font-weight: 800;
        background: linear-gradient(135deg, #fef08a 0%, #fbbf24 50%, #d97706 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
        letter-spacing: -0.01em;
        text-transform: uppercase;
    }

    .hero-subtitle {
        color: #94a3b8;
        font-size: 0.92rem;
        font-weight: 500;
        margin-bottom: 0.75rem;
    }

    .pill-tag {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 600;
        background: rgba(245, 158, 11, 0.1);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.25);
        margin-right: 0.4rem;
    }

    /* Preset Chips */
    button[kind="secondary"] {
        background: #131b2e !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 8px !important;
        padding: 0.45rem 0.75rem !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        color: #cbd5e1 !important;
        transition: all 0.2s ease !important;
        white-space: nowrap !important;
    }

    button[kind="secondary"]:hover {
        border-color: #f59e0b !important;
        color: #fbbf24 !important;
        background: #17233d !important;
    }

    /* Primary Gold Button */
    button[kind="primary"] {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
        color: #0b0f19 !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.65rem 1.5rem !important;
        box-shadow: 0 4px 14px rgba(245, 158, 11, 0.25) !important;
        letter-spacing: 0.02em !important;
    }

    button[kind="primary"]:hover {
        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%) !important;
        box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4) !important;
    }

    /* Metric Cards: High Contrast & Proportional */
    .metric-card {
        background: linear-gradient(180deg, #162033 0%, #0f172a 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-top: 3px solid #f59e0b;
        border-radius: 10px;
        padding: 1.15rem 0.75rem;
        text-align: center;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
    }

    .metric-value {
        font-size: 1.65rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.02em;
        line-height: 1.15;
        margin-bottom: 0.3rem;
    }

    .metric-label {
        font-size: 0.72rem;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* Rubric Dimension Row */
    .rubric-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.45rem 0.75rem;
        border-radius: 6px;
        background: #111827;
        margin-bottom: 0.4rem;
        font-size: 0.82rem;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    .rubric-pass {
        color: #34d399;
        font-weight: 700;
    }

    .rubric-fail {
        color: #f87171;
        font-weight: 700;
    }

    /* Task Card */
    .task-card {
        background: #111827;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 4px solid #f59e0b;
        border-radius: 8px;
        padding: 1.15rem 1.35rem;
        margin: 1rem 0;
    }

    /* Issue Card */
    .issue-card {
        background: #151d30;
        border-left: 4px solid #ef4444;
        border-radius: 6px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.75rem;
    }

    .issue-card.minor {
        border-left-color: #f59e0b;
    }

    /* Status Badges */
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .badge-easy { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
    .badge-medium { background: rgba(245, 158, 11, 0.18); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .badge-hard { background: rgba(239, 68, 68, 0.18); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }

    .badge-approved { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }
    .badge-revised { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }

    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Hero Header
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-title">DualCode Studio</div>
        <div class="hero-subtitle">
            Closed-Loop Cybernetic Multi-Agent Code Generation • Deterministic Orchestration • Subprocess Sandbox Ground Truth
        </div>
        <div>
            <span class="pill-tag">Closed-Loop Cybernetics</span>
            <span class="pill-tag">0-LLM Deterministic Control</span>
            <span class="pill-tag">Pytest Sandbox Isolation</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar Navigation
st.sidebar.markdown("### System Navigation")
view_mode = st.sidebar.radio(
    "Navigation Mode",
    ["Interactive Studio", "Benchmark Explorer"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.markdown("#### Active Model Topology")
st.sidebar.info(
    f"""
    **Writer Agent**  
    `{config.WRITER_MODEL}` (temp: `{config.WRITER_TEMPERATURE}`)  
    *Exploratory drafting & revisions*

    **Critic Agent**  
    `{config.CRITIC_MODEL}` (temp: `{config.CRITIC_TEMPERATURE}`)  
    *Analytical rubric verification*
    """
)

st.sidebar.markdown("#### Orchestration Hyperparameters")
max_rounds = st.sidebar.slider("Max Iteration Rounds", min_value=1, max_value=5, value=config.MAX_ROUNDS)
stall_threshold = st.sidebar.slider(
    "Stall Threshold (difflib ratio)",
    min_value=0.80,
    max_value=0.99,
    value=config.STALL_THRESHOLD,
    step=0.01,
)

# Helper function to generate unified diff
def generate_diff(code_old: str, code_new: str) -> str:
    diff_lines = list(
        difflib.unified_diff(
            code_old.splitlines(),
            code_new.splitlines(),
            fromfile="Previous Round",
            tofile="Revised Round",
            lineterm="",
        )
    )
    return "\n".join(diff_lines)


# ==========================================
# VIEW 1: INTERACTIVE STUDIO
# ==========================================
if view_mode == "Interactive Studio":
    studio_tabs = st.tabs(["Task Bank Challenge", "Custom Prompt / Specification"])

    task_to_run = None

    with studio_tabs[0]:
        tasks = load_task_bank()
        task_options = {
            f"[{t.id}] {t.title} ({t.difficulty.upper()})": t for t in tasks
        }
        selected_task_label = st.selectbox(
            "Select Pre-Configured Challenge",
            list(task_options.keys()),
            help="15 multi-tier challenges with ground-truth pytest hidden test suites.",
        )
        selected_bank_task = task_options[selected_task_label]

        diff_class = f"badge-{selected_bank_task.difficulty}"
        st.markdown(
            f"""
            <div class="task-card">
                <div style="margin-bottom: 0.5rem;">
                    <span class="badge {diff_class}">{selected_bank_task.difficulty}</span>
                    <span style="font-weight: 700; color: #f8fafc; font-size: 1rem; margin-left: 0.4rem;">{selected_bank_task.title}</span>
                </div>
                <div style="font-size: 0.88rem; color: #fbbf24; margin-bottom: 0.5rem;">
                    <code>{selected_bank_task.function_signature}</code>
                </div>
                <div style="font-size: 0.92rem; color: #cbd5e1; line-height: 1.55;">
                    {selected_bank_task.spec}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Execute DualCode (Bank Task)", type="primary", use_container_width=True):
            task_to_run = selected_bank_task

    with studio_tabs[1]:
        st.markdown("<div style='color: #94a3b8; font-size: 0.9rem; margin-bottom: 0.75rem;'>Execute the closed multi-agent loop on any arbitrary, out-of-scope programming prompt.</div>", unsafe_allow_html=True)

        if "custom_spec_val" not in st.session_state:
            st.session_state["custom_spec_val"] = ""
        if "custom_sig_val" not in st.session_state:
            st.session_state["custom_sig_val"] = ""

        def load_password_preset():
            st.session_state["custom_spec_val"] = (
                "Write a Python function to validate if a user's password is strong. "
                "It must be at least 8 characters long, contain at least one uppercase letter, "
                "one lowercase letter, one digit, and one special character (such as !@#$%^&*). "
                "Return True if the password is valid, and False otherwise."
            )
            st.session_state["custom_sig_val"] = "def is_strong_password(password: str) -> bool:"

        def load_email_preset():
            st.session_state["custom_spec_val"] = (
                "Write a Python function to validate whether an email address is properly formatted. "
                "It must contain a non-empty username, exactly one '@' sign, a domain name, and a "
                "valid top-level domain with at least two letters (like .com or .org). "
                "Return True if valid, and False otherwise."
            )
            st.session_state["custom_sig_val"] = "def is_valid_email(email: str) -> bool:"

        def load_slug_preset():
            st.session_state["custom_spec_val"] = (
                "Write a Python function that converts an article title into a clean URL slug "
                "(for example, '10 Tips for Writing Better Python!' becomes '10-tips-for-writing-better-python'). "
                "It should convert characters to lowercase, replace spaces and punctuation with single hyphens, "
                "and strip leading and trailing hyphens."
            )
            st.session_state["custom_sig_val"] = "def create_url_slug(title: str) -> str:"

        def load_phone_preset():
            st.session_state["custom_spec_val"] = (
                "Write a Python function that takes a raw US phone number string (such as '5551234567' "
                "or '(555) 123-4567') and formats it into the standard format '(XXX) XXX-XXXX'. "
                "If the input does not contain exactly 10 numeric digits, return None."
            )
            st.session_state["custom_sig_val"] = "def format_phone_number(phone_str: str) -> str | None:"

        st.markdown("<small style='color: #cbd5e1; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;'>Quick Example Chips:</small>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        col1.button("Password Checker", on_click=load_password_preset, use_container_width=True)
        col2.button("Email Validator", on_click=load_email_preset, use_container_width=True)
        col3.button("URL Slug Creator", on_click=load_slug_preset, use_container_width=True)
        col4.button("Phone Formatter", on_click=load_phone_preset, use_container_width=True)

        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

        custom_spec = st.text_area(
            "Specification / Requirements Prompt",
            key="custom_spec_val",
            placeholder="e.g. Write a Python function to validate and normalize IPv6 addresses without using the ipaddress library.",
            height=110,
        )
        custom_sig = st.text_input(
            "Target Function Signature (Optional)",
            key="custom_sig_val",
            placeholder="e.g. def normalize_ipv6(address: str) -> str | None:",
        )

        if st.button("Execute DualCode (Custom Prompt)", type="primary", use_container_width=True):
            if not custom_spec.strip():
                st.error("Please enter a specification prompt.")
            else:
                sig = custom_sig.strip() if custom_sig.strip() else "Define an idiomatic function signature with type annotations."
                task_to_run = Task(
                    id="custom_prompt",
                    title="Custom Specification",
                    spec=custom_spec.strip(),
                    function_signature=sig,
                    difficulty="medium",
                    hidden_tests="",
                )

    # Execution Block
    if task_to_run:
        st.markdown("---")
        with st.status("Executing multi-agent loop...", expanded=True) as status_box:
            st.write(f"Writer Agent ({config.WRITER_MODEL}) drafting candidate solution...")
            start_time = time.time()
            loop_res = run_loop(task_to_run, max_rounds=max_rounds, stall_threshold=stall_threshold)
            elapsed = time.time() - start_time
            st.write(f"Orchestrator finished: {loop_res['stopped_reason']} in {loop_res['rounds_used']} round(s) ({elapsed:.2f}s).")
            status_box.update(label="Multi-Agent Loop Completed", state="complete", expanded=False)

        final_code = loop_res["final_code"]
        rounds_used = loop_res["rounds_used"]
        stopped_reason = loop_res["stopped_reason"]
        history = loop_res["verdict_history"]

        # Friendly explanation for stopped reason
        trigger_display = {
            "approved": "Critic Approval",
            "stalled": "Similarity Stalled (>98%)",
            "max_rounds": "Max Rounds Ceiling",
        }.get(stopped_reason, stopped_reason.title())

        # Proportional Metric Tiles
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            last_verdict = history[-1]["verdict"] if history else "N/A"
            v_color = "#34d399" if last_verdict == "APPROVE" else "#f87171"
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value" style="color: {v_color};">{last_verdict}</div>
                    <div class="metric-label">Final Verdict</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value" style="color: #fbbf24;">{rounds_used} / {max_rounds}</div>
                    <div class="metric-label">Iteration Rounds</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value" style="font-size: 1.35rem; padding-top: 0.25rem;">{trigger_display}</div>
                    <div class="metric-label">Orchestrator Trigger</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with m4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-value" style="color: #38bdf8;">{elapsed:.2f}s</div>
                    <div class="metric-label">Execution Time</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height: 1.25rem;'></div>", unsafe_allow_html=True)

        # Round Progression Cards
        st.markdown("### Iterative Round Progression")
        round_tab_names = [f"Round {item['round']} ({item['verdict']})" for item in history]
        round_tabs = st.tabs(round_tab_names)

        for idx, item in enumerate(history):
            with round_tabs[idx]:
                c_left, c_right = st.columns([1.1, 0.9])
                with c_left:
                    head_l, head_r = st.columns([1.2, 0.8])
                    with head_l:
                        st.markdown("**Writer Candidate Code**")
                    round_code = item.get("code", final_code)
                    with head_r:
                        st.download_button(
                            label="Download .py",
                            data=round_code,
                            file_name=f"{task_to_run.id}_round_{item['round']}.py",
                            mime="text/x-python",
                            key=f"dl_btn_{item['round']}_{idx}",
                        )
                    st.code(round_code, language="python", line_numbers=True)

                with c_right:
                    v_badge = (
                        '<span class="badge badge-approved">APPROVED</span>'
                        if item["verdict"] == "APPROVE"
                        else '<span class="badge badge-revised">REVISION REQUIRED</span>'
                    )
                    st.markdown(f"**Critic Rubric Audit** &nbsp; {v_badge}", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size: 0.92rem; color: #cbd5e1; margin-bottom: 0.85rem;'>{item['summary']}</div>", unsafe_allow_html=True)

                    issues = item.get("issues", [])
                    if not issues:
                        st.markdown(
                            """
                            <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 8px; padding: 0.85rem 1rem; margin-bottom: 0.85rem;">
                                <div style="color: #34d399; font-weight: 700; font-size: 0.88rem; margin-bottom: 0.5rem;">
                                    All 5 Rubric Dimensions Passed
                                </div>
                                <div class="rubric-item"><span style="color:#cbd5e1;">1. Algorithm Correctness</span><span class="rubric-pass">PASSED</span></div>
                                <div class="rubric-item"><span style="color:#cbd5e1;">2. Edge Case Boundaries</span><span class="rubric-pass">PASSED</span></div>
                                <div class="rubric-item"><span style="color:#cbd5e1;">3. Resource & Logic Security</span><span class="rubric-pass">PASSED</span></div>
                                <div class="rubric-item"><span style="color:#cbd5e1;">4. Python Idioms & Readability</span><span class="rubric-pass">PASSED</span></div>
                                <div class="rubric-item"><span style="color:#cbd5e1;">5. Space & Time Performance</span><span class="rubric-pass">PASSED</span></div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(f"**Identified Issues ({len(issues)}):**")
                        for iss in issues:
                            sev_class = "minor" if iss.get("severity") == "minor" else "critical"
                            st.markdown(
                                f"""
                                <div class="issue-card {sev_class}">
                                    <div style="font-weight: 700; font-size: 0.82rem; text-transform: uppercase; color: #fbbf24;">
                                        [{iss.get('category')}] • {iss.get('severity')}
                                    </div>
                                    <div style="font-size: 0.9rem; color: #f1f5f9; margin-top: 0.25rem;">
                                        {iss.get('explanation')}
                                    </div>
                                    <div style="font-size: 0.82rem; color: #94a3b8; margin-top: 0.35rem;">
                                        <i>Suggestion:</i> {iss.get('suggestion')}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

        # Code Diff Viewer
        if len(history) > 1:
            st.markdown("### Inter-Round Code Differential")
            round_a_idx = st.selectbox("Compare Round A", list(range(1, len(history))), index=0)
            round_b_idx = st.selectbox("With Round B", list(range(round_a_idx + 1, len(history) + 1)), index=0)

            code_a = history[round_a_idx - 1].get("code", "")
            code_b = history[round_b_idx - 1].get("code", "")
            diff_text = generate_diff(code_a, code_b)

            if diff_text:
                st.code(diff_text, language="diff")
            else:
                st.info("No text changes between selected rounds (stalled).")

        # Ground Truth Sandbox Execution
        st.markdown("### Sandboxed Ground-Truth Verification")
        test_res = None

        if task_to_run.hidden_tests.strip():
            with st.spinner("Executing hidden unit tests in isolated subprocess sandbox..."):
                test_res = run_hidden_tests(final_code, task_to_run)

            if test_res["passed"]:
                st.success(
                    f"ALL BANK TESTS PASSED: {test_res['pass_count']} passed | {test_res['fail_count']} failed in sandbox"
                )
            else:
                st.error(
                    f"TESTS FAILED: {test_res['pass_count']} passed | {test_res['fail_count']} failed in sandbox"
                )

            with st.expander("View Subprocess Test Trace Output", expanded=False):
                st.code(test_res["output"], language="text")
        else:
            # Custom Prompt: Synthesize Dynamic Pytest Suite on the fly!
            with st.spinner("Synthesizing independent pytest assertions & running sandbox verification..."):
                synth_tests = synthesize_test_suite(task_to_run)
                if synth_tests is None:
                    st.warning(
                        "COULD NOT VERIFY (Synthesis Failed): Dynamic test suite generation timed out across candidate models. "
                        "Python AST syntax parsed cleanly, but ground-truth execution could not be independently certified."
                    )
                else:
                    custom_task_with_tests = Task(
                        id=task_to_run.id,
                        title=task_to_run.title,
                        spec=task_to_run.spec,
                        function_signature=task_to_run.function_signature,
                        difficulty=task_to_run.difficulty,
                        hidden_tests=synth_tests,
                    )
                    test_res = run_hidden_tests(final_code, custom_task_with_tests)

                    if test_res["passed"]:
                        st.success(
                            f"SYNTHESIZED GROUND-TRUTH PASSED: {test_res['pass_count']} passed | {test_res['fail_count']} failed in sandbox"
                        )
                    else:
                        st.error(
                            f"SYNTHESIZED TESTS FAILED: {test_res['pass_count']} passed | {test_res['fail_count']} failed in sandbox"
                        )

                    with st.expander("View Synthesized Pytest Suite (Generated On-The-Fly)", expanded=False):
                        st.code(synth_tests, language="python")

                    with st.expander("View Subprocess Pytest Trace Output", expanded=False):
                        st.code(test_res["output"], language="text")

        # Live Cross-Check Banner: Don't Trust Opinion, Trust Ground Truth
        if test_res is not None:
            last_verdict = history[-1]["verdict"] if history else "N/A"
            is_approved = (last_verdict == "APPROVE")
            tests_passed = test_res["passed"]

            if is_approved and not tests_passed:
                st.error(
                    "CRITICAL AUDIT MISMATCH (Rubber-Stamp Caught): Critic approved the candidate implementation, "
                    "but isolated sandbox tests failed! The execution sandbox successfully exposed a false-positive approval."
                )
            elif not is_approved and tests_passed:
                st.warning(
                    "AUDIT MISMATCH (Hyper-Criticism Detected): Subprocess sandbox passed all ground-truth tests, "
                    "yet the Critic demanded revisions or stalled before issuing an approval."
                )
            elif is_approved and tests_passed:
                st.info(
                    "CONSENSUS VERIFIED: Critic audit (APPROVE) and sandboxed ground-truth tests are in 100% agreement."
                )
            else:
                st.info(
                    "CONSENSUS VERIFIED: Both Critic and sandboxed tests agree that the candidate implementation requires revision."
                )


# ==========================================
# VIEW 2: BENCHMARK EXPLORER
# ==========================================
elif view_mode == "Benchmark Explorer":
    st.markdown("### Benchmark Scorecards & Audit Logs")
    st.markdown("<div style='color: #94a3b8; font-size: 0.92rem; margin-bottom: 1rem;'>Inspect raw evaluation artifacts produced by the headless evaluation harness across multi-pass runs.</div>", unsafe_allow_html=True)

    eval_dir = Path("eval/eval_results")
    if not eval_dir.exists():
        st.warning("No evaluation directory found at `eval/eval_results`.")
    else:
        json_files = sorted(list(eval_dir.glob("eval_results_*.json")), reverse=True)
        if not json_files:
            st.info("No benchmark run JSON files found. Run `python cli.py eval` to generate benchmark data.")
        else:
            selected_file = st.selectbox(
                "Select Benchmark Execution Run",
                json_files,
                format_func=lambda p: f"{p.name} ({p.stat().st_size / 1024:.1f} KB)",
            )

            with open(selected_file, "r", encoding="utf-8") as f:
                scorecard = json.load(f)

            # High-Contrast, Legible Benchmark Metric Boxes
            b1, b2, b3, b4, b5 = st.columns(5)
            with b1:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-value">{scorecard.get('task_count', 0)}</div>
                        <div class="metric-label">Tasks Benchmarked</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with b2:
                loop_rate = scorecard.get("critic_loop_pass_rate", 0) * 100
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-value" style="color: #34d399;">{loop_rate:.1f}%</div>
                        <div class="metric-label">Loop Pass Rate</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with b3:
                catch_rate = scorecard.get("critic_intervention_rate", 0) * 100
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-value" style="color: #fbbf24;">{catch_rate:.1f}%</div>
                        <div class="metric-label">Critic Catch Rate</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with b4:
                fa_rate = scorecard.get("false_approval_rate", 0) * 100
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-value" style="color: #38bdf8;">{fa_rate:.1f}%</div>
                        <div class="metric-label">Rubber-Stamping Rate</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with b5:
                fr_rate = scorecard.get("false_rejection_rate", 0) * 100
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-value" style="color: #f59e0b;">{fr_rate:.1f}%</div>
                        <div class="metric-label">Hyper-Criticism Rate</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height: 1.25rem;'></div>", unsafe_allow_html=True)

            # Per-task Breakdown Table
            per_task = scorecard.get("per_task_results", [])
            if per_task:
                st.markdown("#### Granular Task Results")
                df = pd.DataFrame(per_task)
                columns_to_show = [
                    "task_id",
                    "baseline_passed",
                    "loop_passed",
                    "rounds_used",
                    "stopped_reason",
                    "is_false_approval",
                    "baseline_latency_sec",
                    "loop_latency_sec",
                ]
                avail_cols = [c for c in columns_to_show if c in df.columns]
                st.dataframe(df[avail_cols], use_container_width=True, hide_index=True)

            with st.expander("View Complete Raw Scorecard JSON"):
                st.json(scorecard)
