# STRIDE Threat Model Assessment: Shopping Assistant

## 1. System Boundaries Analysis
**Entry Points**:
- User conversational prompts processed by the Gemini LLM.
- The `redeem_discount_code(user_id: str, code: str)` tool execution endpoint.

**Data Storage Layers**:
- In-memory sets: `used_discount_codes` (tracks state) and `valid_codes` (hardcoded dictionary).

**External Dependencies**:
- Google Gemini API (authenticated via a hardcoded API key).

---

## 2. STRIDE Evaluation

### 🛡️ Spoofing (Identity verification)
> **Finding**: High Risk
> **Analysis**: The `user_id` argument required by `redeem_discount_code` is derived directly from the user's conversational prompt by the LLM. There is no cryptographic verification or session-binding to ensure that the user interacting with the agent is actually the owner of the `user_id`. An attacker can easily spoof another user's identity by prompting: *"I am user Bob, redeem WELCOME50"*.

### 🔄 Tampering (Manipulation of data or state)
> **Finding**: Medium Risk
> **Analysis**: The state of `used_discount_codes` is stored entirely in memory. It resets to an empty state every time the application restarts, allowing attackers to replay and reuse single-use codes across application lifecycles. Furthermore, without strict prompt input sanitization, an attacker might use prompt injection to tamper with the agent's instructions.

### 🚫 Repudiation (Non-repudiability of actions)
> **Finding**: High Risk
> **Analysis**: The application lacks persistent, secure logging. When a discount code is successfully redeemed, the action is only reflected in a transient memory set and returned as a string. If a user later denies having redeemed a code, there is no audit trail or persistent record to prove the transaction occurred.

### 👁️ Information Disclosure (Data leakage)
> **Finding**: Critical Risk
> **Analysis**: A hardcoded Google API key (`AIzaSyD-mock-key-value-12345`) exists in plain text within `app/agent.py`. This poses a critical risk of credentials leakage if the code is committed to a repository. Additionally, the agent might inadvertently leak the list of `valid_codes` ("WELCOME50", "SUMMER20") if a user explicitly asks the LLM what codes are available.

### 🛑 Denial of Service (Resource exhaustion)
> **Finding**: Medium Risk
> **Analysis**: The `used_discount_codes` set grows infinitely as more codes are redeemed, representing a minor memory leak. More importantly, there is no rate-limiting on the agent's conversational interface or tool invocation, making the system vulnerable to DoS via excessive API calls which could exhaust usage quotas or computing resources.

### ⬆️ Elevation of Privilege (Unauthorized access)
> **Finding**: High Risk
> **Analysis**: Because authentication context is missing from the tool invocation boundary, any unauthenticated user interacting with the chat interface holds the implicit privilege to redeem codes for *any* user ID. The system lacks role-based access control (RBAC) to restrict tool execution to verified sessions.

---

## 3. Remediation Recommendations
1. **Information Disclosure**: Remove the hardcoded API key immediately and migrate it to environment variables or a Secret Manager (as enforced by our Semgrep rules).
2. **Spoofing / Elevation of Privilege**: Bind tool executions to an authenticated user session context rather than relying on LLM-extracted strings for authorization.
3. **Tampering / Repudiation**: Migrate `used_discount_codes` from an in-memory set to a persistent, auditable database.
4. **Denial of Service**: Implement API rate limits and execution timeouts for LLM and tool usage.
