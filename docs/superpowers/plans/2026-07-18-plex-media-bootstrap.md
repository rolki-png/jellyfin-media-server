# Plex Media Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a greenfield Node CLI that lets a Linux first-timer pick Plex-stack services, generate Compose, bring containers up, and auto-wire them via APIs — built entirely with TDD vertical slices.

**Architecture:** TypeScript CLI (`plex-bootstrap`) renders Docker Compose from service modules, writes `.env` + folder skeleton, runs `docker compose up`, then executes idempotent wire steps against each app’s HTTP API. Output is plain Compose with no proprietary runtime after generate.

**Tech Stack:** Node.js ≥22, TypeScript, Vitest, Commander, `@inquirer/prompts`, `yaml`, native `fetch`, Docker Compose v2 on Linux.

## Global Constraints

- **TDD mandatory:** no production code without a failing test first; vertical RED→GREEN→refactor only; behavior through public interfaces; delete-and-rewrite if code preceded its test.
- **Host:** Linux + Docker Engine + Compose v2 only (no macOS/Windows in v1).
- **Core services (always generated):** Plex, Seerr, Sonarr, Radarr, Prowlarr, qBittorrent.
- **Opt-in:** Jackett, FlareSolverr, Unpackerr, Bazarr, Tautulli, Recyclarr, Gluetun (qBit only).
- **Out of v1:** Jellyfin, Traefik/SSO, web UI.
- **Images (pin in modules):** `lscr.io/linuxserver/{plex,sonarr,radarr,prowlarr,qbittorrent,jackett,bazarr,tautulli}:latest`, `ghcr.io/seerr-team/seerr:latest`, `ghcr.io/flaresolverr/flaresolverr:latest`, `ghcr.io/unpackerr/unpackerr:latest`, `ghcr.io/recyclarr/recyclarr:8`, `qmcgaw/gluetun:latest`.
- **Paths:** single host root `${DATA_ROOT}` mounted as `/data` in containers; `media/{movies,tv}`, `torrents/{movies,tv}`, `configs/<app>`.
- **Networks:** `media` + `download`; *arr join both; qBit (± Gluetun) on `download`.
- **New repo location:** `/home/rolki/projects/plex-bootstrap` (git init, separate from All-jellyfin-media-server).
- **Package name:** `plex-bootstrap`; bin: `plex-bootstrap`.
- **Recyclarr:** scheduled one-shot container (`recyclarr sync` on cron via compose), not a long-lived daemon API.

---

## File Structure

```
plex-bootstrap/
  package.json
  tsconfig.json
  vitest.config.ts
  src/
    index.ts                 # CLI entry (commander)
    types.ts                 # StackConfig, WireResult, etc.
    doctor/
      index.ts               # runDoctor(): DoctorReport
      checks.ts              # individual check functions
    generate/
      index.ts               # generateStack(config, outDir): GenerateResult
      merge.ts               # merge modules → compose object
      modules/               # one file per service exporting ServiceModule
        plex.ts
        seerr.ts
        sonarr.ts
        radarr.ts
        prowlarr.ts
        qbittorrent.ts
        jackett.ts
        flaresolverr.ts
        unpackerr.ts
        bazarr.ts
        tautulli.ts
        recyclarr.ts
        gluetun.ts
      folders.ts             # ensureFolderSkeleton
      env.ts                 # renderEnvFile
    wire/
      index.ts               # runWire(config, state): WireReport
      state.ts               # load/save state.json
      http.ts                # small fetch helper
      steps/
        qbittorrent.ts
        sonarr.ts
        radarr.ts
        prowlarr.ts
        seerr.ts
        extras.ts            # unpackerr/bazarr/tautulli/jackett notes
    cli/
      init.ts
      wire.ts
      doctor.ts
      up.ts
    prompts/
      initPrompts.ts         # interactive StackConfig builder
  tests/
    doctor.test.ts
    generate.test.ts
    generate-snapshots.test.ts
    wire-qbittorrent.test.ts
    wire-sonarr.test.ts
    wire-radarr.test.ts
    wire-prowlarr.test.ts
    wire-seerr.test.ts
    wire-orchestrator.test.ts
    init-orchestration.test.ts
  fixtures/
    apis/                    # optional recorded response shapes
  README.md
  .gitignore
```

---

### Task 1: Scaffold greenfield repo + first public type

**Files:**
- Create: `/home/rolki/projects/plex-bootstrap/package.json`
- Create: `/home/rolki/projects/plex-bootstrap/tsconfig.json`
- Create: `/home/rolki/projects/plex-bootstrap/vitest.config.ts`
- Create: `/home/rolki/projects/plex-bootstrap/.gitignore`
- Create: `/home/rolki/projects/plex-bootstrap/src/types.ts`
- Test: `/home/rolki/projects/plex-bootstrap/tests/types-smoke.test.ts`

**Interfaces:**
- Produces: `StackConfig`, `CoreServices`, `OptionalServices`, `VpnConfig` types used by all later tasks.

- [ ] **Step 1: Create repo and package scaffolding**

```bash
mkdir -p /home/rolki/projects/plex-bootstrap
cd /home/rolki/projects/plex-bootstrap
git init
npm init -y
npm pkg set name=plex-bootstrap version=0.1.0 type=module
npm pkg set bin.plex-bootstrap=./dist/index.js
npm pkg set scripts.build="tsc -p tsconfig.json"
npm pkg set scripts.test="vitest run"
npm pkg set scripts.test:watch="vitest"
npm install -D typescript vitest @types/node
npm install commander @inquirer/prompts yaml
```

`tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "declaration": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*"]
}
```

`vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["tests/**/*.test.ts"],
  },
});
```

`.gitignore`:

```
node_modules/
dist/
.env
state.json
coverage/
*.log
```

- [ ] **Step 2: Write the failing test for StackConfig shape helpers**

Create `tests/types-smoke.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { defaultStackConfig, isCoreComplete } from "../src/types.ts";

describe("StackConfig", () => {
  it("defaultStackConfig enables all core services and no extras", () => {
    const cfg = defaultStackConfig({
      dataRoot: "/data",
      configRoot: "/data/configs",
      puid: 1000,
      pgid: 1000,
      timezone: "UTC",
    });
    expect(cfg.services.plex).toBe(true);
    expect(cfg.services.seerr).toBe(true);
    expect(cfg.services.sonarr).toBe(true);
    expect(cfg.services.radarr).toBe(true);
    expect(cfg.services.prowlarr).toBe(true);
    expect(cfg.services.qbittorrent).toBe(true);
    expect(cfg.services.jackett).toBe(false);
    expect(cfg.services.vpn).toBe(false);
    expect(isCoreComplete(cfg)).toBe(true);
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /home/rolki/projects/plex-bootstrap && npm test -- tests/types-smoke.test.ts`
Expected: FAIL (cannot find module `../src/types.ts`)

- [ ] **Step 4: Write minimal `src/types.ts`**

```ts
export type ServiceFlags = {
  plex: boolean;
  seerr: boolean;
  sonarr: boolean;
  radarr: boolean;
  prowlarr: boolean;
  qbittorrent: boolean;
  jackett: boolean;
  flaresolverr: boolean;
  unpackerr: boolean;
  bazarr: boolean;
  tautulli: boolean;
  recyclarr: boolean;
  vpn: boolean;
};

export type VpnConfig = {
  provider: string;
  username: string;
  password: string;
  openvpnUser?: string;
  openvpnPassword?: string;
};

export type StackConfig = {
  dataRoot: string;
  configRoot: string;
  puid: number;
  pgid: number;
  timezone: string;
  plexClaim?: string;
  services: ServiceFlags;
  vpn?: VpnConfig;
};

export function defaultStackConfig(
  base: Pick<StackConfig, "dataRoot" | "configRoot" | "puid" | "pgid" | "timezone">,
): StackConfig {
  return {
    ...base,
    services: {
      plex: true,
      seerr: true,
      sonarr: true,
      radarr: true,
      prowlarr: true,
      qbittorrent: true,
      jackett: false,
      flaresolverr: false,
      unpackerr: false,
      bazarr: false,
      tautulli: false,
      recyclarr: false,
      vpn: false,
    },
  };
}

export function isCoreComplete(cfg: StackConfig): boolean {
  const s = cfg.services;
  return s.plex && s.seerr && s.sonarr && s.radarr && s.prowlarr && s.qbittorrent;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test -- tests/types-smoke.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /home/rolki/projects/plex-bootstrap
git add package.json package-lock.json tsconfig.json vitest.config.ts .gitignore src/types.ts tests/types-smoke.test.ts
git commit -m "chore: scaffold plex-bootstrap with StackConfig types"
```

---

### Task 2: `doctor` preflight checks

**Files:**
- Create: `src/doctor/checks.ts`
- Create: `src/doctor/index.ts`
- Test: `tests/doctor.test.ts`

**Interfaces:**
- Consumes: none from Task 1 beyond shared repo.
- Produces: `runDoctor(deps?: DoctorDeps): Promise<DoctorReport>` where `DoctorReport = { ok: boolean; checks: Array<{ name: string; ok: boolean; detail: string }> }`.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from "vitest";
import { runDoctor } from "../src/doctor/index.ts";

describe("runDoctor", () => {
  it("reports ok when docker, compose, and writable data root are available", async () => {
    const report = await runDoctor({
      which: async (cmd) => (cmd === "docker" ? "/usr/bin/docker" : null),
      exec: async (cmd) => {
        if (cmd.includes("compose version")) return { code: 0, stdout: "Docker Compose version v2.30.0", stderr: "" };
        if (cmd.includes("docker info")) return { code: 0, stdout: "Server:", stderr: "" };
        return { code: 1, stdout: "", stderr: "unknown" };
      },
      canWrite: async () => true,
      dataRoot: "/data",
    });
    expect(report.ok).toBe(true);
    expect(report.checks.map((c) => c.name)).toEqual(
      expect.arrayContaining(["docker", "compose", "docker-daemon", "data-root-writable"]),
    );
  });

  it("fails when docker binary is missing", async () => {
    const report = await runDoctor({
      which: async () => null,
      exec: async () => ({ code: 1, stdout: "", stderr: "" }),
      canWrite: async () => true,
      dataRoot: "/data",
    });
    expect(report.ok).toBe(false);
    expect(report.checks.find((c) => c.name === "docker")?.ok).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/doctor.test.ts`
Expected: FAIL (module not found)

- [ ] **Step 3: Write minimal implementation**

`src/doctor/checks.ts`:

```ts
export type ExecResult = { code: number; stdout: string; stderr: string };

export type DoctorDeps = {
  which: (cmd: string) => Promise<string | null>;
  exec: (cmd: string) => Promise<ExecResult>;
  canWrite: (path: string) => Promise<boolean>;
  dataRoot: string;
};

export type DoctorCheck = { name: string; ok: boolean; detail: string };
```

`src/doctor/index.ts`:

```ts
import type { DoctorCheck, DoctorDeps } from "./checks.ts";

export type DoctorReport = { ok: boolean; checks: DoctorCheck[] };

export async function runDoctor(deps: DoctorDeps): Promise<DoctorReport> {
  const checks: DoctorCheck[] = [];

  const dockerPath = await deps.which("docker");
  checks.push({
    name: "docker",
    ok: Boolean(dockerPath),
    detail: dockerPath ? `found at ${dockerPath}` : "docker not found on PATH",
  });

  const compose = await deps.exec("docker compose version");
  checks.push({
    name: "compose",
    ok: compose.code === 0 && /v2\./i.test(compose.stdout),
    detail: compose.stdout.trim() || compose.stderr.trim() || "compose v2 required",
  });

  const info = await deps.exec("docker info");
  checks.push({
    name: "docker-daemon",
    ok: info.code === 0,
    detail: info.code === 0 ? "daemon reachable" : info.stderr || "cannot reach docker daemon",
  });

  const writable = await deps.canWrite(deps.dataRoot);
  checks.push({
    name: "data-root-writable",
    ok: writable,
    detail: writable ? `${deps.dataRoot} writable` : `${deps.dataRoot} not writable`,
  });

  return { ok: checks.every((c) => c.ok), checks };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/doctor.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/doctor tests/doctor.test.ts
git commit -m "feat: add injectable doctor preflight checks"
```

---

### Task 3: Generate core Compose (no extras)

**Files:**
- Create: `src/generate/modules/*.ts` for core six services + shared networks helper
- Create: `src/generate/merge.ts`
- Create: `src/generate/index.ts`
- Create: `src/generate/env.ts`
- Test: `tests/generate.test.ts`

**Interfaces:**
- Consumes: `StackConfig` from `src/types.ts`
- Produces: `generateStack(config, outDir): Promise<GenerateResult>` writing `docker-compose.yml` + `.env`; `GenerateResult = { composePath: string; envPath: string; services: string[] }`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from "vitest";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse as parseYaml } from "yaml";
import { defaultStackConfig } from "../src/types.ts";
import { generateStack } from "../src/generate/index.ts";

describe("generateStack core", () => {
  it("writes compose with plex seerr sonarr radarr prowlarr qbittorrent and shared /data mounts", async () => {
    const outDir = await mkdtemp(join(tmpdir(), "pb-gen-"));
    const cfg = defaultStackConfig({
      dataRoot: "/data",
      configRoot: "/data/configs",
      puid: 1000,
      pgid: 1000,
      timezone: "Europe/Budapest",
    });
    const result = await generateStack(cfg, outDir);
    const raw = await readFile(result.composePath, "utf8");
    const doc = parseYaml(raw) as { services: Record<string, unknown>; networks: Record<string, unknown> };

    expect(Object.keys(doc.services).sort()).toEqual(
      ["plex", "prowlarr", "qbittorrent", "radarr", "seerr", "sonarr"].sort(),
    );
    expect(doc.networks).toHaveProperty("media");
    expect(doc.networks).toHaveProperty("download");
    expect(result.services).toEqual(expect.arrayContaining(["plex", "sonarr"]));

    const env = await readFile(result.envPath, "utf8");
    expect(env).toContain("PUID=1000");
    expect(env).toContain("TZ=Europe/Budapest");
    expect(env).toContain("DATA_ROOT=/data");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/generate.test.ts`
Expected: FAIL (generateStack not found)

- [ ] **Step 3: Write minimal modules + generateStack**

Define `ServiceModule` in `src/generate/merge.ts`:

```ts
export type ServiceModule = {
  name: string;
  service: Record<string, unknown>;
};

export function mergeCompose(modules: ServiceModule[]): Record<string, unknown> {
  const services: Record<string, unknown> = {};
  for (const m of modules) services[m.name] = m.service;
  return {
    networks: {
      media: { name: "pb_media" },
      download: { name: "pb_download" },
    },
    services,
  };
}
```

Each core module exports `buildX(cfg: StackConfig): ServiceModule` with linuxserver-style env `PUID/PGID/TZ`, volumes `${DATA_ROOT}/configs/<app>:/config` and `${DATA_ROOT}:/data`, networks as specified in Global Constraints. Plex uses `network_mode: host` **or** ports `32400:32400` — for v1 use published port `32400:32400` on `media` network (simpler for first-timers than host mode; document claim URL).

`src/generate/env.ts` renders:

```
PUID=
PGID=
TZ=
DATA_ROOT=
CONFIG_ROOT=
PLEX_CLAIM=
```

`src/generate/index.ts` selects core modules when flags true, merges, writes YAML via `yaml.stringify`, writes `.env`.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/generate.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/generate tests/generate.test.ts
git commit -m "feat: generate core plex compose and env from StackConfig"
```

---

### Task 4: Generate opt-in extras + VPN

**Files:**
- Modify: `src/generate/index.ts` (module selection)
- Create: remaining `src/generate/modules/{jackett,flaresolverr,unpackerr,bazarr,tautulli,recyclarr,gluetun}.ts`
- Modify: `src/generate/modules/qbittorrent.ts` (when vpn: no published ports; network_mode service:gluetun)
- Test: `tests/generate-snapshots.test.ts`

**Interfaces:**
- Consumes: `generateStack`, `StackConfig.services.*`
- Produces: same `generateStack`; when `services.vpn`, compose includes `gluetun` and qBit uses `network_mode: "service:gluetun"`

- [ ] **Step 1: Write the failing tests**

```ts
import { describe, expect, it } from "vitest";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { parse as parseYaml } from "yaml";
import { defaultStackConfig } from "../src/types.ts";
import { generateStack } from "../src/generate/index.ts";

async function gen(services: Partial<ReturnType<typeof defaultStackConfig>["services"]>, vpn?: object) {
  const outDir = await mkdtemp(join(tmpdir(), "pb-snap-"));
  const cfg = defaultStackConfig({
    dataRoot: "/data",
    configRoot: "/data/configs",
    puid: 1000,
    pgid: 1000,
    timezone: "UTC",
  });
  Object.assign(cfg.services, services);
  if (vpn) cfg.vpn = vpn as never;
  const result = await generateStack(cfg, outDir);
  const doc = parseYaml(await readFile(result.composePath, "utf8")) as {
    services: Record<string, { network_mode?: string; networks?: string[] }>;
  };
  return doc;
}

describe("generateStack extras", () => {
  it("includes jackett flaresolverr unpackerr bazarr tautulli recyclarr when enabled", async () => {
    const doc = await gen({
      jackett: true,
      flaresolverr: true,
      unpackerr: true,
      bazarr: true,
      tautulli: true,
      recyclarr: true,
    });
    for (const name of ["jackett", "flaresolverr", "unpackerr", "bazarr", "tautulli", "recyclarr"]) {
      expect(doc.services).toHaveProperty(name);
    }
  });

  it("wraps qbittorrent with gluetun when vpn enabled", async () => {
    const doc = await gen(
      { vpn: true },
      { provider: "protonvpn", username: "u", password: "p" },
    );
    expect(doc.services).toHaveProperty("gluetun");
    expect(doc.services.qbittorrent.network_mode).toBe("service:gluetun");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- tests/generate-snapshots.test.ts`
Expected: FAIL (missing services / network_mode)

- [ ] **Step 3: Implement extra modules + VPN branching**

When `cfg.services.vpn`:
- Add gluetun module with `VPN_SERVICE_PROVIDER`, credentials from `cfg.vpn`, ports for qBit WebUI published on gluetun (`8080:8080`).
- qBit service: `network_mode: "service:gluetun"`, no `ports`, no `networks` key, `depends_on: [gluetun]`.

Recyclarr module: image `ghcr.io/recyclarr/recyclarr:8` (Recyclarr no longer publishes `:latest`), command `sync`, restart `unless-stopped` with a note in labels that schedule is via host cron **or** use `recyclarr` container with documented manual `docker compose run` — for v1 define service:

```yaml
recyclarr:
  image: ghcr.io/recyclarr/recyclarr:8
  user: "${PUID}:${PGID}"
  volumes:
    - ${CONFIG_ROOT}/recyclarr:/config
  environment:
    - TZ=${TZ}
  profiles: ["manual"]
```

Actually profiles conflict with “generated only if opted”. If opted in, include service with `restart: "no"` and document `docker compose run --rm recyclarr sync`. Prefer:

```yaml
command: ["sync"]
restart: unless-stopped
```

only if image supports long-running schedule; otherwise generate a `recyclarr` service intended for `compose run`. **Decision locked in plan:** opted Recyclarr = service with `entrypoint: ["recyclarr"]`, `command: ["sync"]`, `restart: "no"` — user/docs run on a timer via `wire` printing a cron line. Test only asserts service key exists.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- tests/generate-snapshots.test.ts`
Expected: PASS

- [ ] **Step 5: Also assert `docker compose config` when docker available**

Add test (skip if no docker):

```ts
it("generated core compose passes docker compose config", async () => {
  // spawn sync: docker compose -f <path> --env-file <env> config
  // skip if docker missing
});
```

- [ ] **Step 6: Commit**

```bash
git add src/generate tests/generate-snapshots.test.ts
git commit -m "feat: generate optional extras and gluetun vpn wrap"
```

---

### Task 5: Folder skeleton

**Files:**
- Create: `src/generate/folders.ts`
- Modify: `src/generate/index.ts` to call it
- Test: extend `tests/generate.test.ts`

**Interfaces:**
- Produces: `ensureFolderSkeleton(config): Promise<string[]>` creating `media/movies`, `media/tv`, `torrents/movies`, `torrents/tv`, `configs/<enabled apps>`

- [ ] **Step 1: Write the failing test**

```ts
it("creates hardlink-safe folder skeleton under dataRoot", async () => {
  const outDir = await mkdtemp(join(tmpdir(), "pb-gen-"));
  const dataRoot = await mkdtemp(join(tmpdir(), "pb-data-"));
  const cfg = defaultStackConfig({
    dataRoot,
    configRoot: join(dataRoot, "configs"),
    puid: 1000,
    pgid: 1000,
    timezone: "UTC",
  });
  await generateStack(cfg, outDir);
  const { access } = await import("node:fs/promises");
  for (const p of [
    join(dataRoot, "media/movies"),
    join(dataRoot, "media/tv"),
    join(dataRoot, "torrents/movies"),
    join(dataRoot, "torrents/tv"),
    join(dataRoot, "configs/sonarr"),
  ]) {
    await access(p);
  }
});
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL (ENOENT)

- [ ] **Step 3: Implement `ensureFolderSkeleton` and call from `generateStack`**

- [ ] **Step 4: Run tests — PASS**

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: create data/media/torrents/configs folder skeleton"
```

---

### Task 6: Wire HTTP helper + state store

**Files:**
- Create: `src/wire/http.ts`
- Create: `src/wire/state.ts`
- Test: `tests/wire-state.test.ts`

**Interfaces:**
- Produces:
  - `apiJson<T>(url, init & { apiKey?: string }): Promise<T>`
  - `loadState(path): Promise<WireState>` / `saveState(path, state)`
  - `WireState = { apiKeys: Record<string, string>; completedSteps: string[]; failedSteps: string[] }`

- [ ] **Step 1: Write failing tests for load/save round-trip and apiJson header injection**

Use Vitest mock of global `fetch` for `apiJson`.

- [ ] **Step 2: Verify FAIL**

- [ ] **Step 3: Minimal implementation**

- [ ] **Step 4: Verify PASS**

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add wire http helper and state.json persistence"
```

---

### Task 7: Wire qBittorrent categories + paths

**Files:**
- Create: `src/wire/steps/qbittorrent.ts`
- Test: `tests/wire-qbittorrent.test.ts`

**Interfaces:**
- Consumes: `apiJson`, `StackConfig`
- Produces: `wireQbittorrent(ctx: WireContext): Promise<StepResult>`  
  `StepResult = { name: string; ok: boolean; detail: string; fallback?: string }`  
  `WireContext = { config: StackConfig; state: WireState; baseUrls: Record<string, string>; fetchFn?: typeof fetch }`

Behavior:
- Login / set cookie if needed (qBit uses cookie auth — implement cookie jar in step).
- Ensure categories `movies` and `tv` with save paths `/data/torrents/movies` and `/data/torrents/tv`.

- [ ] **Step 1: Write failing test with mocked fetch sequence (login → setCategory ×2)**

- [ ] **Step 2: FAIL**

- [ ] **Step 3: Implement step**

- [ ] **Step 4: PASS**

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: wire qbittorrent categories and save paths"
```

---

### Task 8: Wire Sonarr + Radarr (root folders + download client)

**Files:**
- Create: `src/wire/steps/sonarr.ts`
- Create: `src/wire/steps/radarr.ts`
- Test: `tests/wire-sonarr.test.ts`
- Test: `tests/wire-radarr.test.ts`

**Interfaces:**
- Produces: `wireSonarr(ctx)`, `wireRadarr(ctx)` → `StepResult`
- Ensures root folder `/data/media/tv` or `/data/media/movies`
- Ensures download client pointing at host `qbittorrent` (or `gluetun` WebUI host when VPN — use `http://gluetun:8080` vs `http://qbittorrent:8080` based on `config.services.vpn`)
- Category `tv` / `movies` respectively
- Idempotent: if client named `qBittorrent` exists, update not duplicate

- [ ] **Step 1: Failing tests for create + idempotent second run**

- [ ] **Step 2: FAIL**

- [ ] **Step 3: Implement both steps (share small `ensureDownloadClient` helper in `src/wire/steps/arr-shared.ts` only if both need it — extract on third duplication, not before)**

- [ ] **Step 4: PASS**

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: wire sonarr and radarr root folders and qbittorrent client"
```

---

### Task 9: Wire Prowlarr app sync (+ FlareSolverr tag)

**Files:**
- Create: `src/wire/steps/prowlarr.ts`
- Test: `tests/wire-prowlarr.test.ts`

**Interfaces:**
- Produces: `wireProwlarr(ctx): Promise<StepResult>`
- Adds Sonarr/Radarr as apps in Prowlarr using stored API keys from state
- If `flaresolverr` enabled, ensure indexer proxy entry for FlareSolverr at `http://flaresolverr:8191`

- [ ] **Step 1: Failing test with mocked Prowlarr API**

- [ ] **Step 2: FAIL → Step 3: implement → Step 4: PASS → Step 5: Commit**

```bash
git commit -am "feat: wire prowlarr to sonarr radarr and optional flaresolverr"
```

---

### Task 10: Wire Seerr to Plex + Sonarr + Radarr

**Files:**
- Create: `src/wire/steps/seerr.ts`
- Test: `tests/wire-seerr.test.ts`

**Interfaces:**
- Produces: `wireSeerr(ctx): Promise<StepResult>`
- Connects media server Plex (using claim/settings as API allows) and Sonarr/Radarr servers with API keys from state
- On failure, `fallback` string lists UI URL `http://localhost:5055` and fields to set

- [ ] **Step 1–5: TDD cycle + commit**

```bash
git commit -am "feat: wire seerr to plex sonarr and radarr"
```

---

### Task 11: Wire extras (Unpackerr, Bazarr, Tautulli, Jackett note)

**Files:**
- Create: `src/wire/steps/extras.ts`
- Test: `tests/wire-extras.test.ts`

**Interfaces:**
- Produces: `wireExtras(ctx): Promise<StepResult[]>`
- Unpackerr: ensure Sonarr/Radarr in unpackerr config via API/env if available; if config-file only, write config snippet under `configs/unpackerr` and return ok with detail
- Bazarr: add Sonarr/Radarr
- Tautulli: connect Plex URL
- Jackett: no deep sync — return ok with Torznab base URL note for manual indexer add

- [ ] **Step 1–5: TDD cycle + commit**

```bash
git commit -am "feat: wire optional extras with jackett fallback notes"
```

---

### Task 12: Wire orchestrator + `--retry`

**Files:**
- Create: `src/wire/index.ts`
- Test: `tests/wire-orchestrator.test.ts`

**Interfaces:**
- Produces: `runWire(ctx, opts?: { retryFailedOnly?: boolean }): Promise<WireReport>`
- `WireReport = { ok: boolean; coreOk: boolean; steps: StepResult[] }`
- Order: qBit → Sonarr → Radarr → Prowlarr → Seerr → extras
- Isolated try/catch per step
- `coreOk` false if Sonarr/Radarr↔qBit or Seerr↔*arr steps failed
- Process exit semantics handled by CLI (Task 13): exit 1 if `!coreOk`
- `retryFailedOnly` skips steps not in `state.failedSteps`

- [ ] **Step 1: Write failing tests**

```ts
it("continues after a non-core step failure and records failedSteps", async () => { /* ... */ });
it("retryFailedOnly re-runs only failed steps", async () => { /* ... */ });
it("sets coreOk false when sonarr download client step fails", async () => { /* ... */ });
```

- [ ] **Step 2: FAIL → Step 3: implement `runWire` → Step 4: PASS → Step 5: Commit**

```bash
git commit -am "feat: orchestrate wire steps with isolated failures and retry"
```

---

### Task 13: CLI commands (`doctor`, `init`, `wire`, `up`, `down`, `update`)

**Files:**
- Create: `src/index.ts`
- Create: `src/cli/doctor.ts`, `init.ts`, `wire.ts`, `up.ts`
- Create: `src/prompts/initPrompts.ts`
- Test: `tests/init-orchestration.test.ts`

**Interfaces:**
- Produces: Commander program with subcommands
- `init`: prompts (injectable for tests) → `runDoctor` → `generateStack` → `dockerComposeUp` → `runWire`
- Inject `DockerCompose` port: `{ up(dir), down(dir), pull(dir) }` for tests

- [ ] **Step 1: Write failing orchestration test**

```ts
it("init runs doctor generate up wire in order when doctor ok", async () => {
  const calls: string[] = [];
  await runInit({
    prompt: async () => defaultStackConfig({ /* tmp paths */ }),
    doctor: async () => ({ ok: true, checks: [] }),
    generate: async () => { calls.push("generate"); return { composePath: "...", envPath: "...", services: [] }; },
    compose: { up: async () => { calls.push("up"); }, down: async () => {}, pull: async () => {} },
    wire: async () => { calls.push("wire"); return { ok: true, coreOk: true, steps: [] }; },
    outDir: "/tmp/pb-out",
  });
  expect(calls).toEqual(["generate", "up", "wire"]);
});

it("init aborts before generate when doctor fails", async () => {
  await expect(
    runInit({
      prompt: async () => defaultStackConfig({ dataRoot: "/data", configRoot: "/data/configs", puid: 1000, pgid: 1000, timezone: "UTC" }),
      doctor: async () => ({ ok: false, checks: [{ name: "docker", ok: false, detail: "missing" }] }),
      generate: async () => { throw new Error("should not run"); },
      compose: { up: async () => {}, down: async () => {}, pull: async () => {} },
      wire: async () => ({ ok: true, coreOk: true, steps: [] }),
      outDir: "/tmp/pb-out",
    }),
  ).rejects.toThrow(/doctor/i);
});
```

- [ ] **Step 2: FAIL → Step 3: implement `runInit` + commander wiring → Step 4: PASS**

- [ ] **Step 5: Manual smoke (not CI):** `node dist/index.js doctor --data-root /tmp/pb-data`

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: add CLI init wire doctor up down update commands"
```

---

### Task 14: README + first-run docs

**Files:**
- Create: `README.md`
- Create: `docs/wiring-fallback.md`

**Interfaces:** none (docs only — no TDD; allowed exception for documentation)

- [ ] **Step 1: Write README covering prerequisites, `npx`/`npm start` init flow, core vs extras, VPN, hardlink layout, TRaSH link, fallback doc link**

- [ ] **Step 2: Write `docs/wiring-fallback.md` with per-app UI field tables matching wire fallback strings**

- [ ] **Step 3: Commit**

```bash
git add README.md docs/wiring-fallback.md
git commit -m "docs: add first-run README and wiring fallback guide"
```

---

### Task 15: End-to-end manual acceptance script

**Files:**
- Create: `scripts/manual-acceptance.md` (checklist from spec)
- Create: `tests/generate-compose-config.test.ts` if not already covering `docker compose config` for core/+vpn/+extras

- [ ] **Step 1: Ensure three generation fixtures pass `docker compose config`**

- [ ] **Step 2: Commit**

```bash
git commit -am "test: validate generated compose via docker compose config"
```

- [ ] **Step 3: Run full `npm test` — all green**

- [ ] **Step 4: Tag `v0.1.0` locally (do not npm publish unless user asks)**

```bash
git tag v0.1.0
```

---

## Spec coverage check

| Spec requirement | Task |
|------------------|------|
| Greenfield Node CLI | 1, 13 |
| Linux doctor preflight | 2 |
| Core services generate | 3 |
| Opt-in extras + VPN | 4 |
| Hardlink folder layout | 5 |
| Auto-wire APIs + idempotency | 6–12 |
| Isolated failures + retry | 12 |
| `init` / `wire` / `doctor` / compose wrappers | 13 |
| First-timer docs + fallbacks | 14 |
| Success criteria / compose config | 15 |
| TDD vertical slices | Every code task Steps 1–4 |
| No Jellyfin/Traefik/web UI | Honored (not scheduled) |

## Placeholder / consistency review

- Types: `StackConfig`, `StepResult`, `WireReport`, `DoctorReport` named consistently across tasks.
- qBit URL host: `qbittorrent` vs `gluetun` branched on `services.vpn` in Task 8.
- No TBD left in task steps; open naming was locked to `plex-bootstrap`.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-18-plex-media-bootstrap.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — execute tasks in this session with executing-plans checkpoints  

Which approach?
