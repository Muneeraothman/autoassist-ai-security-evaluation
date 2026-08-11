# Framework Reference (current as of this review, Aug 2026)

Looked up rather than recalled from memory, since both frameworks move
fast. Cited here once; test cases and the findings table reference these
short codes rather than re-explaining them each time.

## OWASP Top 10 for LLM Applications — 2025 edition

Source: [OWASP GenAI Security Project](https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/).

| Code | Category |
|---|---|
| LLM01:2025 | Prompt Injection |
| LLM02:2025 | Sensitive Information Disclosure |
| LLM03:2025 | Supply Chain |
| LLM04:2025 | Data and Model Poisoning |
| LLM05:2025 | Improper Output Handling |
| LLM06:2025 | Excessive Agency |
| LLM07:2025 | System Prompt Leakage |
| LLM08:2025 | Vector and Embedding Weaknesses |
| LLM09:2025 | Misinformation |
| LLM10:2025 | Unbounded Consumption |

Notable reordering vs. the older 2023/2024 list this project's original
build guide was written against: Sensitive Information Disclosure jumped
from 6th to 2nd; System Prompt Leakage and Vector/Embedding Weaknesses are
now their own top-level categories rather than folded into others. Test
case mappings below use this 2025 numbering, not the older one.

## MITRE ATLAS — techniques used in this review's mappings

Source: [atlas.mitre.org](https://atlas.mitre.org/), current as of the
Spring/Fall 2025 technique expansion (Generative AI / RAG / agent
coverage).

| ID | Technique | Tactic |
|---|---|---|
| AML.T0051.000 | LLM Prompt Injection: Direct | Initial Access |
| AML.T0051.001 | LLM Prompt Injection: Indirect | Initial Access |
| AML.T0056 | Extract LLM System Prompt (meta-prompt extraction) | Exfiltration |
| AML.T0057 | LLM Data Leakage | Exfiltration |
| AML.T0070 | RAG Poisoning | Resource Development / ML Attack Staging |
| AML.T0029 | Denial of ML Service (inference-API abuse to exhaust resources / inflate cost) | Impact |

Two of this review's categories (cross-user authorization bypass via tool
misuse, and hallucination/ungrounded advice) don't have a single clean
1:1 ATLAS technique — ATLAS models the *mechanism* an attacker uses
(prompt injection, data leakage) more granularly than the *consequence*
(an authorization bypass, a false statement). Where that's the case, the
findings table names the ATLAS technique that would be the *mechanism* an
attacker would need (typically AML.T0051, prompt injection, used to
attempt an excessive-agency outcome) and notes OWASP's LLM06 (Excessive
Agency) as the more precise category for the consequence itself, rather
than forcing an inexact ATLAS ID.
