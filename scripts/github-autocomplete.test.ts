import { afterEach, expect, mock, test } from "bun:test";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

// These tests exercise routing and session/cache behavior, not fuzzy matching.
mock.module("@earendil-works/pi-tui", () => ({
  fuzzyFilter: (items: any[], query: string, text: (item: any) => string) =>
    items.filter((item) => text(item).includes(query)),
}));
const { default: extension } = await import("../.pi/extensions/github-issues-autocomplete/index");
const cleanups: Array<() => Promise<void>> = [];
afterEach(async () => {
  for (const cleanup of cleanups.splice(0)) await cleanup();
});

async function until(check: () => Promise<boolean>) {
  for (let i = 0; i < 400; i++) {
    if (await check()) return;
    await Bun.sleep(5);
  }
  throw new Error("Timed out waiting for autocomplete refresh");
}

async function harness() {
  const cwd = await mkdtemp(join(tmpdir(), "herdr-autocomplete-"));
  const handlers: Record<string, any> = {};
  const providers: any[] = [];
  const calls: string[][] = [];
  const state = {
    repo: "nantas/herdr", fail: false, origin: true, resolveFail: false,
    detailWait: undefined as Promise<void> | undefined, detailStarted: false,
  };
  const exec = async (command: string, args: string[]) => {
    if (command === "git") return {
      code: state.origin ? 0 : 1, stdout: `git@github.com:${state.repo}.git`, stderr: "",
    };
    if (args[0] === "repo") return {
      code: state.resolveFail ? 1 : 0, stdout: JSON.stringify({ owner: { login: state.repo.split("/")[0] }, name: "herdr" }), stderr: "",
    };
    calls.push(args);
    if (args[1] === "view" && state.detailWait) {
      state.detailStarted = true;
      await state.detailWait;
    }
    if (state.fail) return { code: 1, stdout: "", stderr: "offline" };
    // Reproduce gh's implicit upstream selection in a fork with two remotes.
    const repoIndex = args.indexOf("--repo");
    const repo = repoIndex < 0 ? "herdrdev/herdr" : args[repoIndex + 1];
    const item = {
      number: args[1] === "view" ? Number(args[2]) : 10,
      title: `${repo} ${args[0]}`, labels: [], author: { login: "author" },
      updatedAt: "2026-10-22T00:00:00Z", state: "OPEN", headRefName: "feature", isDraft: false,
    };
    return { code: 0, stdout: JSON.stringify(args[1] === "list" ? [item] : item), stderr: "" };
  };
  await extension({ exec, on: (name: string, fn: any) => { handlers[name] = fn; } } as any);
  const ctx = { cwd, ui: { addAutocompleteProvider: (factory: any) => providers.push(factory({
    getSuggestions: async () => null, applyCompletion: () => null,
  })) } };
  const suggestions = (input: string, provider = providers.at(-1)) => provider.getSuggestions(
    [input], 0, input.length, { signal: new AbortController().signal },
  );
  const cache = (repo: string, extra = {}) => ({
    repo: { owner: repo.split("/")[0], repo: "herdr", fullName: repo },
    issues: [{ number: 99, title: "cached", labels: "", author: "", updatedAt: "" }],
    prs: [], fetchedAt: new Date(Date.now() + 60_000).toISOString(), ...extra,
  });
  const write = async (value: any) => {
    await mkdir(join(ctx.cwd, ".pi/cache"), { recursive: true });
    await writeFile(join(ctx.cwd, ".pi/cache/github-refs.json"), JSON.stringify(value));
  };
  cleanups.push(async () => { await handlers.session_shutdown(); await rm(cwd, { recursive: true, force: true }); });
  return { ctx, state, calls, handlers, providers, suggestions, cache, write,
    start: () => handlers.session_start({}, ctx) };
}

test("origin routes both lists and numeric lookups to the fork, including inserted references", async () => {
  const h = await harness();
  await h.start();
  await until(async () => (await h.suggestions("@issue:"))?.items[0]?.label.includes("issue"));
  expect((await h.suggestions("@issue:"))?.items[0]).toMatchObject({
    value: "issue nantas/herdr#10", label: "#10 nantas/herdr issue",
  });
  expect((await h.suggestions("@issue:42"))?.items[0].value).toBe("issue nantas/herdr#42");
  expect((await h.suggestions("@pr:43"))?.items[0]).toMatchObject({
    value: "pr nantas/herdr#43", label: "#43 nantas/herdr pr",
  });
  await until(async () => h.calls.some((args) => args[0] === "pr" && args[1] === "list"));
  for (const args of h.calls) expect(args.slice(args.indexOf("--repo"), args.indexOf("--repo") + 2))
    .toEqual(["--repo", "nantas/herdr"]);
});

test("legacy cache is discarded even when its claimed repo matches and Github fails", async () => {
  const h = await harness();
  await h.write(h.cache("nantas/herdr"));
  h.state.fail = true;
  await h.start();
  expect(await h.suggestions("@issue:")).toBeNull();
});

test("cache updates from another repo never replace the current repo", async () => {
  const h = await harness();
  await h.start();
  await until(async () => (await h.suggestions("@issue:"))?.items.length > 0);
  await h.write(h.cache("herdrdev/herdr", { routingVersion: 1 }));
  expect((await h.suggestions("@issue:"))?.items[0].value).toBe("issue nantas/herdr#10");
});

test("a new session directory resolves its own repo and preserves single-remote fallback", async () => {
  const h = await harness();
  await h.start();
  await until(async () => (await h.suggestions("@issue:"))?.items.length > 0);
  h.ctx.cwd = join(h.ctx.cwd, "other");
  await mkdir(h.ctx.cwd);
  h.state.repo = "other/herdr";
  h.state.origin = false;
  await h.start();
  await until(async () => (await h.suggestions("@issue:"))?.items.length > 0);
  expect((await h.suggestions("@issue:"))?.items[0]).toMatchObject({
    value: "issue other/herdr#10", label: "#10 other/herdr issue",
  });
});


test("verified same-repo cache survives Github failure without refreshing its timestamp", async () => {
  const h = await harness();
  const cached = h.cache("nantas/herdr", { routingVersion: 1 });
  await h.write(cached);
  h.state.fail = true;
  await h.start();
  expect((await h.suggestions("@issue:"))?.items[0].value).toBe("issue nantas/herdr#99");
  expect(await h.suggestions("@pr:42")).toBeNull();
  const disk = JSON.parse(await readFile(join(h.ctx.cwd, ".pi/cache/github-refs.json"), "utf8"));
  expect(disk.fetchedAt).toBe(cached.fetchedAt);
});

test("unresolved repository does not query lists or numeric details using gh defaults", async () => {
  const h = await harness();
  h.state.origin = false;
  h.state.resolveFail = true;
  await h.write(h.cache("nantas/herdr", { routingVersion: 1 }));
  await h.start();
  expect(await h.suggestions("@issue:42")).toBeNull();
  expect(await h.suggestions("@pr:42")).toBeNull();
  expect(h.calls).toEqual([]);
});

test("a late detail response is discarded after switching sessions", async () => {
  const h = await harness();
  await h.start();
  await until(async () => (await h.suggestions("@issue:"))?.items.length > 0);
  let release!: () => void;
  h.state.detailWait = new Promise<void>((resolve) => { release = resolve; });
  const oldProvider = h.providers.at(-1);
  const pending = h.suggestions("@issue:42", oldProvider);
  await until(async () => h.state.detailStarted);
  h.ctx.cwd = join(h.ctx.cwd, "other");
  await mkdir(h.ctx.cwd);
  h.state.repo = "other/herdr";
  await h.start();
  release();
  expect(await pending).toBeNull();
  expect(await h.suggestions("@issue:", oldProvider)).toBeNull();
  await until(async () => (await h.suggestions("@issue:"))?.items.length > 0);
  expect((await h.suggestions("@issue:"))?.items.map((item: any) => item.value))
    .toEqual(["issue other/herdr#10"]);
});

test("agent instructions keep the explicit repository in list and detail commands", async () => {
  const h = await harness();
  expect(await h.handlers.before_agent_start({ messageType: "custom", message: {} })).toBeUndefined();
  const nudge = await h.handlers.before_agent_start({ prompt: "issue nantas/herdr#2 pr nantas/herdr#20" });
  for (const command of ["issue view <number>", "issue list", "pr view <number>", "pr list"]) {
    expect(nudge.message.content).toContain(`gh ${command} --repo <owner/repo>`);
  }
});
