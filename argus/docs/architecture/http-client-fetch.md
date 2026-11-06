# Architecture Specification: Fetch

## 1. Executive Summary & Problem Statement

In a default Tauri architecture, the frontend runs inside an operating system Webview (WebKit on Linux/macOS, WebView2 on Windows). Standard browser security mechanisms block outbound network requests triggered via `window.fetch()`.

While the official `@tauri-apps/plugin-http` provides a bypass, it requires static registration of permitted endpoints upfront in application capabilities.

### Challenges in Argus
1. **Dynamic Endpoints at Runtime**: Argus interacts with dynamically discovered endpoints (microservices, simulation orchestration engines like Dynawo/GameMaster/Scada, local sidecars, and pluggable user extensions) whose hostnames and ports cannot be known at compile time.
2. **Transparent Developer Experience (DX)**: Third-party SDKs, npm packages (e.g., Axios), and standard frontend code must work transparently with vanilla `fetch(url, options)` without wrapping calls in custom proprietary SDK functions.
3. **Enterprise Environment Compliance**: All outbound HTTP traffic must respect corporate proxy settings (`HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`) configured in Argus settings and react to runtime configuration updates without requiring application restarts.

---

## 2. Global System Architecture

The solution uses a hybrid **Pre-Script Monkey-Patch + IPC Bridge + Native Actor Pool** architecture:

```mermaid
graph TB
    subgraph WebviewContext ["1. Webview Runtime (Browser Environment)"]
        UI["Application Code / Libraries<br><code>fetch(url)</code>, <code>axios.get()</code>"]
        Patch["Early Boot Monkey-Patch<br><code>public/pre-fetch.js</code>"]
        Queue["Memory FIFO Queue<br><code>requestQueue[]</code>"]
        Bridge["Fetch Bridge Service<br><code>FetchBridgeService (Effect-TS)</code>"]
        Parser["Unified URL Parser<br><code>parseBridgeUrl()</code>"]
        TSRegistry["Frontend Client Registry<br><code>HttpClientRegistry</code>"]
    end

    subgraph IPCTransport ["2. Inter-Process Communication"]
        IPC["Tauri Binary IPC Invoke<br><code>invoke('get' | 'post' | 'sse', ...)</code>"]
        Channel["Tauri Async Channel<br><code>Channel&lt;String&gt; (SSE Streaming)</code>"]
    end

    subgraph RustRuntime ["3. Native Tauri Core (Rust Engine)"]
        Cmd["HTTP Command Handlers<br><code>src-tauri/src/http/commands.rs</code>"]
        Prep["Request Prep & Security Resolver<br><code>prepare_request()</code>"]
        RustRegistry["Backend Client Registry<br><code>HttpManager::clients</code>"]
        ClientMgr["Client Manager ('direct' & Extensions)<br><code>ClientManager</code>"]
        Actor["Async Worker Actor<br><code>tokio::mpsc::channel</code>"]
        ReqwestPool["Native HTTP Engine Pool<br><code>reqwest::Client</code>"]
        ProxyWatcher["Proxy Watcher & Auto-Reconnect<br><code>ConfigManager::settings</code>"]
    end

    subgraph RemoteNetwork ["4. Network Target"]
        TargetServer["Remote APIs / Sidecars / Simulation Nodes"]
    end

    UI -->|1. Call window.fetch| Patch
    Patch -->|2a. Internal resource| BrowserNative["Native Webview Fetch"]
    Patch -->|2b. If bridge not ready| Queue
    Queue -->|Flush on 'argus:bridge-ready'| Bridge
    Patch -->|2c. If bridge ready| Bridge

    Bridge -->|3. Validate & resolve clientId| Parser
    Bridge -->|4. Get or create client| TSRegistry
    TSRegistry -->|5. Forward request| IPC
    TSRegistry -.->|Optional SSE stream| Channel

    IPC -->|6. Dispatch command| Cmd
    Channel -->|Stream SSE events| Bridge
    Cmd -->|7. Prepare & resolve| Prep
    Prep -->|8. Fetch client instance| RustRegistry
    RustRegistry --> ClientMgr
    ClientMgr --> Actor
    Actor -->|9. Execute with connection reuse| ReqwestPool
    ProxyWatcher -.->|Hot reconnect on settings change| ClientMgr
    ReqwestPool -->|10. TCP/TLS Socket| TargetServer

    classDef web fill:#e1f5fe,stroke:#0288d1,stroke-width:1px,color:#01579b;
    classDef ipc fill:#fff3e0,stroke:#f57c00,stroke-width:1px,color:#e65100;
    classDef rust fill:#fbe9e7,stroke:#d84315,stroke-width:1px,color:#bf360c;
    classDef net fill:#ede7f6,stroke:#512da8,stroke-width:1px,color:#311b92;

    class UI,Patch,Queue,Bridge,Parser,TSRegistry,BrowserNative web;
    class IPC,Channel ipc;
    class Cmd,Prep,RustRegistry,ClientMgr,Actor,ReqwestPool,ProxyWatcher rust;
    class TargetServer net;
```

---

## 3. Detailed Component Interaction & End-to-End Flow

### 3.1 Sequence Diagram: Standard and SSE Requests

```mermaid
sequenceDiagram
    autonumber
    actor Caller as Frontend Caller (fetch / axios)
    participant Patch as pre-fetch.js
    participant Bridge as FetchBridgeService (TS)
    participant TSReg as HttpClientRegistry (TS)
    participant IPC as Tauri IPC Channel
    participant Rust as HttpManager (Rust)
    participant Sec as Security & Resolver (Rust)
    participant Actor as Client Actor & reqwest
    actor Server as Target HTTP Server

    Caller->>Patch: window.fetch(url, options)

    alt Local resource (ipc://, tauri://, /assets/...)
        Patch-->>Caller: originalFetch(url, options)
    else External URL (http://, https://, alias://)
        alt Bridge initialization in-flight
            Patch->>Patch: Push to requestQueue[]
            Note over Patch: Wait for 'argus:bridge-ready' event
        end
        Patch->>Bridge: bridgeInstance.execute(input, init)
        Bridge->>Bridge: parseBridgeUrl(url)
        Note over Bridge: URL matched: clientId = 'direct', actualUrl = url

        Bridge->>TSReg: getClient("direct")
        alt Not in TypeScript memory cache
            TSReg->>TSReg: Instantiate makeTauriHttpClient("direct")
            TSReg->>TSReg: Store in Ref<HashMap>
        end
        TSReg-->>Bridge: Active TauriHttpClient instance

        alt Standard Request (GET, POST, PUT, DELETE, ...)
            Bridge->>IPC: invoke(method, { clientId: "direct", reqId, endpoint, headers, body })
            IPC->>Rust: prepare_request(&app_handle, &http_manager, "direct", endpoint, headers)
            Rust->>Sec: verify_endpoint_access(manager, "direct", endpoint)
            Note over Sec: Direct http(s) detected: BYPASS whitelist check
            Rust->>Sec: resolve_endpoint(manager, "direct", endpoint, headers)
            Note over Sec: Direct http(s) detected: Return target URL as-is
            Rust->>Actor: Dispatch Cancellable Request
            Actor->>Server: HTTP TCP/TLS Request (Socket Pool + Corporate Proxy)
            Server-->>Actor: HTTP Response (Status, Headers, Stream/Bytes)
            Actor-->>IPC: Binary Frame: [Metadata 4-bytes len | JSON Metadata | Body Bytes]
            IPC-->>Bridge: ArrayBuffer
            Bridge-->>Caller: Standard W3C Response Object
        else Streaming SSE Request (Accept: text/event-stream)
            Bridge->>IPC: invoke("sse", { clientId: "direct", reqId, endpoint, headers, onEvent: Channel })
            IPC->>Rust: Start SSE Stream Actor
            Rust->>Server: HTTP GET (Accept: text/event-stream)
            loop Active Event Stream
                Server-->>Rust: Chunk / Event Line
                Rust-->>IPC: Channel.send(event_string)
                IPC-->>Bridge: Channel.onmessage(event_string)
                Bridge-->>Caller: ReadableStream Chunk Output
            end
            Server-->>Rust: Connection closed / [CLOSE]
            Rust-->>IPC: Channel.send("[CLOSE]")
            Bridge-->>Caller: Stream Close
        end
    end
```

---

## 4. Subsystem Deep-Dive

### 4.1 URL Parsing Single Source of Truth (`parseBridgeUrl`)

To prevent divergence between what the bridge intercepts and what the schema decodes, `parseBridgeUrl` in `src/services/http-client/fetch-service/interceptor.ts` acts as the single authority:

```mermaid
flowchart TD
    In([Candidate URL String]) --> CheckReserved{Starts with reserved prefix?<br>ipc://, tauri://}
    CheckReserved -- Yes --> RejectNull[Return null<br>Bypass bridge]

    CheckReserved -- No --> CheckHttp{Starts with<br>http:// or https://?}
    CheckHttp -- Yes --> DirectClient["Return { clientId: 'direct', actualUrl: url }"]

    CheckHttp -- No --> CheckRFC{Matches RFC 3986 format?<br>clientId://endpoint/path}
    CheckRFC -- Yes --> ExtRFC["Return { clientId, actualUrl: 'endpoint://path' }"]

    CheckRFC -- No --> CheckLegacy{Matches Extension format?<br>clientId:endpoint://path}
    CheckLegacy -- Yes --> ExtLegacy["Return { clientId, actualUrl: 'endpoint://path' }"]

    CheckLegacy -- No --> InvalidURL[Return null<br>Bypass bridge]

    classDef decision fill:#fff9c4,stroke:#fbc02d,color:#000;
    classDef success fill:#e8f5e9,stroke:#4caf50,color:#2e7d32;
    classDef bypass fill:#f5f5f5,stroke:#9e9e9e,color:#616161;

    class CheckReserved,CheckHttp,CheckRFC,CheckLegacy decision;
    class DirectClient,ExtRFC,ExtLegacy success;
    class RejectNull,InvalidURL bypass;
```

**Invariant Verification Guarantee**:
The property-based test suite (`tests/http-client/fetch/FetchBridge.property.test.ts`) formally proves across 1,000 arbitrary generated Unicode strings that:
$$\forall s \in \text{String},\quad \text{shouldInterceptUrl}(s) \iff (\text{parseBridgeUrl}(s) \neq \text{null})$$

---

### 4.2 Shared Client Lifecycle & Registry Architecture

Instantiating a new native HTTP client per request creates massive overhead (ephemeral port exhaustion, TLS handshakes on every call, inability to share HTTP/1.1 and HTTP/2 Keep-Alive pools). 

The system routes all direct web traffic through a dedicated registered singleton client named `"direct"`:

```mermaid
stateDiagram-v2
    [*] --> Unconfigured: App Launch

    state FrontendRegistry {
        [*] --> TSNotCached
        TSNotCached --> TSCached: First request intercepted
        TSCached --> TSCached: Subsequent requests (Ref lookup)
    }

    state BackendRegistry {
        Unconfigured --> Disconnected: HttpManager::get_or_resolve_client('direct')
        Disconnected --> Connected: Connect with ConfigManager proxy settings
        Connected --> Connected: Handle multiple parallel requests
        Connected --> Reconnecting: ProxyWatcher detects proxy/no_proxy settings update
        Reconnecting --> Connected: Reconnect active client with new proxy rules
    }
```

#### Registry Responsibilities

| Dimension | Frontend (`HttpClientRegistry`) | Backend (`HttpManager`) |
|---|---|---|
| **Storage Primitive** | `Ref<HashMap<string, HttpClient>>` (Effect-TS) | `RwLock<HashMap<String, Arc<ClientManager>>>` |
| **Instance Lifetime** | Application Session Lifetime | Application Session Lifetime |
| **Direct Client Provisioning** | Lazy: instantiated upon first `fetch("http(s)://")` | Lazy: auto-registered with empty whitelist when requested |
| **Keep-Alive & Connection Pooling** | Managed downstream by Tauri IPC | Managed by `reqwest::Client` connection pool |
| **Configuration Synchronization** | Stateless (delegates network options to Rust) | Dynamic: Listens to `ConfigManager` via `tokio::sync::watch` |

---

### 4.3 Proxy Resolution & Dynamic Reconfiguration

Corporate networks require seamless proxy routing, including strict exclusions for internal infrastructure:

```mermaid
flowchart TD
    Request([Outbound Request Target URL]) --> CheckLocal{Is destination IP / Host local?<br>localhost, 127.0.0.1, RFC 1918 Private IP}
    CheckLocal -- Yes --> DirectBypass[Direct Connection<br>Bypass Proxy completely]

    CheckLocal -- No --> ResolveProxy[Resolve Effective Proxy<br>1. ConfigManager Settings<br>2. Env HTTP_PROXY / HTTPS_PROXY / ALL_PROXY]
    ResolveProxy --> HasProxy{Proxy configured?}
    HasProxy -- No --> DirectBypass

    HasProxy -- Yes --> CheckNoProxy{Matches NO_PROXY rules?<br>Settings no_proxy list + Env NO_PROXY}
    CheckNoProxy -- Yes --> DirectBypass
    CheckNoProxy -- No --> RouteThroughProxy[Route through Corporate Proxy<br>reqwest::Proxy::all]

    classDef decision fill:#fff9c4,stroke:#fbc02d,color:#000;
    classDef action fill:#e1f5fe,stroke:#0288d1,color:#01579b;

    class CheckLocal,HasProxy,CheckNoProxy decision;
    class DirectBypass,ResolveProxy,RouteThroughProxy action;
```

---

## 5. Security Architecture & Boundary Model

While direct `http://` and `https://` URLs intentionally bypass static endpoint whitelisting to enable dynamic network interactions, Argus's internal security perimeter remains strictly enforced for extension modules:

```mermaid
flowchart TD
    IncomingURI[Requested URI] --> ProtocolCheck{Starts with http:// or https://?}
    
    ProtocolCheck -- Yes --> DirectFlow[Direct Firehose Flow]
    DirectFlow --> DirectAccess[Bypass allowed_endpoints check]
    DirectAccess --> PassthroughUrl[Preserve target URL unchanged]
    PassthroughUrl --> Execute[Execute via reqwest Native Engine]

    ProtocolCheck -- No --> ExtensionFlow[Extension Alias Flow<br>e.g. extensionId://endpoint/path]
    ExtensionFlow --> LookupManifest[Fetch Extension Manifest & Overrides]
    LookupManifest --> CheckWhitelist{Is alias declared in<br>manifest allowed_endpoints?}
    CheckWhitelist -- No --> Block[Security Block 403 / InvalidState Error<br>Log security warning]
    CheckWhitelist -- Yes --> RewriteUrl[Rewrite alias to manifest base_url + path]
    RewriteUrl --> Execute

    classDef safe fill:#e8f5e9,stroke:#4caf50,color:#2e7d32;
    classDef secure fill:#e1f5fe,stroke:#0288d1,color:#01579b;
    classDef blocked fill:#ffebee,stroke:#e53935,color:#b71c1c;

    class DirectFlow,DirectAccess,PassthroughUrl safe;
    class ExtensionFlow,LookupManifest,CheckWhitelist,RewriteUrl secure;
    class Block blocked;
```

---

## 6. Test Architecture & Quality Matrix

The architecture is covered by automated verification layers across both TypeScript and Rust test runners:

```mermaid
graph LR
    subgraph FrontendTests ["Frontend Test Suite (Vitest)"]
        PBT_TS["Property-Based Tests<br>Fast-check (1,000 runs)"]
        Integration_TS["End-to-End Integration Tests<br>Fetch & Axios & SSE Streaming"]
        Model_TS["Model-Based Tests (MBT)<br>HttpCache State Machine"]
    end

    subgraph BackendTests ["Backend Test Suite (Cargo)"]
        PBT_Rust["Property-Based Tests<br>Proptest (Bypass & Security Whitelist)"]
        Wiremock_Rust["Wiremock Transport Tests<br>GET, POST Binary, SSE, 500 Handling"]
        Concurrency_Rust["Model-Based Concurrency Tests<br>Actor Cancellation & Async Races"]
    end

    PBT_TS --> InvariantGuarantees["Total Guarantees Verified:<br>1. Parser-Predicate Equivalence<br>2. Lossless Binary Payloads<br>3. Zero Socket Leaks<br>4. Whitelist Integrity<br>5. Hot-Reload Safety"]
    Integration_TS --> InvariantGuarantees
    Model_TS --> InvariantGuarantees
    PBT_Rust --> InvariantGuarantees
    Wiremock_Rust --> InvariantGuarantees
    Concurrency_Rust --> InvariantGuarantees
```

### Test Coverage Summary

| Test Domain | File Location | Scope & Assertions |
|---|---|---|
| **Property Equivalence** | `tests/http-client/fetch/FetchBridge.property.test.ts` | Proves `shouldInterceptUrl` $\equiv$ `parseBridgeUrl !== null`, binary body immutability (`Uint8Array`, `ArrayBuffer`, `FormData`, `URLSearchParams`). |
| **Fetch & Axios Integration** | `tests/http-client/fetch/FetchIntegration.test.ts` | Validates native `window.fetch()` and `axios` with standard `https://` URLs, Bearer tokens, query encoding, `AbortController` cancellation, and streaming SSE consumption. |
| **Mock Registry Architecture** | `tests/mocks/index.ts` & `tests/setup.ts` | Validates `ResettableMock` contract with centralized `resetAllMocks()` in `beforeEach()`. |
| **Rust Endpoint Security** | `src-tauri/src/http/tests/property.rs` | Proves `verify_endpoint_access` and `resolve_endpoint` bypass whitelist checks for `http(s)://` while continuing to block unauthorized alias access. |
| **WireMock Transport** | `src-tauri/src/http_client/tests/wiremock.rs` | Verifies real HTTP socket interactions over local wiremock servers (binary payloads, server errors, SSE event stream delivery). |
