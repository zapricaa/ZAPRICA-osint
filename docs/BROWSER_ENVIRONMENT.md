# ZAPRICA — Dedicated Browser Environment Documentation

## 1. Architectural Overview

The Browser Head Agent operates within an isolated, persistent Playwright browser automation environment. Under no circumstances does the browser agent run on the investigator's personal browser or expose local host sessions.

```
+-------------------------------------------------------------------+
|                     BROWSER HEAD AGENT                            |
|             (Supervised Gemini 3.5 Flash Lite)                    |
+---------------------------------+---------------------------------+
                                  |
               +------------------v------------------+
               |        BROWSER POLICY ENGINE        |
               |  (Enforces Domain & Action Policy)  |
               +------------------+------------------+
                                  |
                                  +------------------------------------+
                                  |                                    |
               +------------------v------------------+  +--------------v---------------+
               |       BROWSER SECURITY VALIDATOR    |  |     BROWSER PROFILE MANAGER  |
               | (Blocks SSRF, RFC1918, Cloud IP)    |  | (User-Isolated Outside Git)  |
               +------------------+------------------+  +--------------+---------------+
                                  |                                    |
               +------------------v------------------------------------v---------------+
               |                         BROWSER MANAGER                               |
               |            (Playwright Chromium Persistent Context)                   |
               +-----------------------------------------------------------------------+
```

---

## 2. Browser Profiles & Isolation

- **Directory Isolation**: Browser profiles are maintained per user inside `data/browser_profiles/<user_id>/<profile_name>/`.
- **Git Separation**: The `data/browser_profiles/` folder is explicitly excluded from version control in `.gitignore`.
- **Path Traversal Defense**: All profile identifiers and paths are strictly validated against `..`, `/`, and `\`. Attempts to access directories outside the user's isolated profile root trigger HTTP 400 Bad Request.
- **Persistence**: Cookies, local storage, indexedDB, and cache persist across sessions for authenticated investigations.

---

## 3. Human Login Flow & Session State Machine

To prevent credential theft and avoid triggering anti-bot hurdles, automated form filling for authentication is forbidden. Investigators perform manual authentication.

```
       [DISCONNECTED]
             |
             v (Launch Session)
        [STARTING]
             |
             v (Browser Initialized)
          [READY] <------------------------------------------+
             |                                               |
             +---------> [LOGIN_REQUIRED]                    |
             |                 |                             |
             |                 v (Operator Opening Login)    |
             |          [AUTHENTICATING]                     |
             |                 |                             |
             |                 v (Investigator Confirms)     |
             |       [USER_AUTHENTICATED] -------------------+
             |
             +---------> [BUSY] (Extracting DOM / Screenshot)
             |                 |
             |                 v (Finished)
             |              [READY]
             |
             v (Stop or Error)
     [STOPPED / ERROR]
```

### Confirmation Protocol
When manual authentication is required (e.g. 2FA, SMS code, Captcha):
1. Session transitions to `LOGIN_REQUIRED`.
2. Browser Head sets state to `AUTHENTICATING`.
3. The human investigator opens the visible browser workspace, enters credentials, completes 2FA/Captcha.
4. The investigator clicks **"CONFIRM USER AUTHENTICATED"** (`POST /api/v1/browser/sessions/{session_id}/confirm-authentication`).
5. Only upon receiving this authenticated confirmation does the session transition to `USER_AUTHENTICATED` and return to `READY`.

---

## 4. Website Automation Policies

Every target URL is evaluated against `BrowserPolicyEngine` before navigation or data extraction:

| Policy Mode | Description | Example Domains | Permitted Actions |
| :--- | :--- | :--- | :--- |
| `AUTOMATED_ALLOWED` | Fully automated navigation and structured extraction within scope | Public websites, search indices | `automated_query`, `automated_extract`, `agent_site_control`, `manual_navigate`, `manual_import` |
| `HUMAN_ASSISTED_ONLY` | Operator controls page interactions; AI extracts or imports only | `epieos.com`, `*.gov` | `manual_navigate`, `manual_import` |
| `API_ONLY` | Web automation blocked; must query approved API adapter | Social platforms with strict terms | None via browser |
| `BLOCKED` | Access strictly prohibited | `*.mil`, dark web, unapproved domains | None (HTTP 403) |

---

## 5. Epieos Special Handling

In accordance with Section 2.6 of the specification:
- **Tool ID**: `epieos`
- **Execution Mode**: `HUMAN_ASSISTED_ONLY`
- **Browser Automation**: `false`
- **Automated Queries**: `false`
- **Automated Scraping**: `false`
- **Agent Site Control**: `false`
- **Manual User Access**: `true`
- **Manual Result Import**: `true`

### Workflow
1. The Browser Head navigates to Epieos or directs the user to open it.
2. The investigator conducts the lookup directly in the browser interface.
3. The investigator copies the JSON, text, or export result and submits it via:
   `POST /api/v1/browser/sessions/{session_id}/import-manual-result`
4. The backend stores the raw data as immutable Evidence with full investigator provenance.

---

## 6. Network Security & SSRF Prevention

The `BrowserSecurityValidator` executes pre-flight and redirect checks:
- **Private IP Blocking**: Blocks all RFC 1918 addresses (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
- **Loopback Blocking**: Blocks `127.0.0.0/8` and `::1`.
- **Link-Local & Cloud Metadata Blocking**: Blocks `169.254.169.254` (AWS, GCP, Azure metadata services).
- **DNS Re-Validation**: Resolves domains to IP addresses at navigation time and validates against CIDR denylists. Redirects are hooked via Playwright route handling to verify every intermediate URL hop.
