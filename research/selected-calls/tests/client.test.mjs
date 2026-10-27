import test from "node:test";
import assert from "node:assert/strict";
import { SelectedCallsClient, selectedCallsPolicy } from "../client.mjs";

const now0 = Date.parse("2026-10-27T12:00:00.000Z");
const edit0 = now0 - 5 * 60_000;

function metadata(edit = edit0, { dataEdit = edit, schemaEdit = edit } = {}) {
  return { fields: [{ name: "OBJECTID", type: "esriFieldTypeOID" }, { name: "DIVISION", type: "esriFieldTypeString" }], editingInfo: { lastEditDate: edit, dataLastEditDate: dataEdit, schemaLastEditDate: schemaEdit } };
}

function jsonResponse(payload, url, options = {}) {
  return new Response(JSON.stringify(payload), {
    status: options.status ?? 200,
    headers: { "content-type": "application/json", ...(options.headers ?? {}) },
  });
}

function fixtureTransport({
  groups = [["D41", 7], ["D42", 5], ["D43", 4]],
  count = groups.reduce((n, [, value]) => n + value, 0),
  beforeEdit = edit0,
  afterEdit = beforeEdit,
  beforeDataEdit = beforeEdit,
  afterDataEdit = beforeDataEdit,
  beforeSchemaEdit = beforeEdit,
  afterSchemaEdit = beforeSchemaEdit,
  groupedPatch = {},
  omitTransferFlag = false,
  countAfter = count,
  beforeMetadataPatch = {},
  afterMetadataPatch = {},
  responseAt = -1,
} = {}) {
  let callIndex = 0;
  const calls = [];
  const fetchImpl = async (url, init) => {
    const index = callIndex++;
    calls.push({ url: new URL(url), init });
    if (responseAt === index) return jsonResponse({ error: { message: "synthetic failure" } }, url);
    if (index === 0) return jsonResponse({ ...metadata(beforeEdit, { dataEdit: beforeDataEdit, schemaEdit: beforeSchemaEdit }), ...beforeMetadataPatch }, url);
    if (index === 1) return jsonResponse({ count }, url);
    if (index === 2) return jsonResponse({
      features: groups.map(([division, call_count]) => ({ attributes: { DIVISION: division, call_count } })),
      ...(omitTransferFlag ? {} : { exceededTransferLimit: false }),
      ...groupedPatch,
    }, url);
    if (index === 3) return jsonResponse({ count: countAfter }, url);
    if (index === 4) return jsonResponse({ ...metadata(afterEdit, { dataEdit: afterDataEdit, schemaEdit: afterSchemaEdit }), ...afterMetadataPatch }, url);
    throw new Error("unexpected extra request");
  };
  return { fetchImpl, calls };
}

function harness(options = {}) {
  const time = { wall: now0, mono: 1_000 };
  const transport = fixtureTransport(options);
  const client = new SelectedCallsClient({
    fetchImpl: transport.fetchImpl,
    now: () => time.wall,
    monotonicNow: () => time.mono,
  });
  client.setVisible(true);
  return { ...transport, client, time };
}

test("valid synthetic aggregate uses five bounded requests and exposes only division counts", async () => {
  const { client, calls } = harness();
  const state = await client.load();
  assert.equal(state.status, "available");
  assert.deepEqual(state.counts, [
    { division: "D41", count: 7 },
    { division: "D42", count: 5 },
    { division: "D43", count: 4 },
  ]);
  assert.equal(calls.length, 5);
  assert.deepEqual(calls.map(({ url }) => url.pathname), [
    "/S9th0jAJ7bqgIRjw/arcgis/rest/services/C4S_Public_NoGO/FeatureServer/0",
    "/S9th0jAJ7bqgIRjw/arcgis/rest/services/C4S_Public_NoGO/FeatureServer/0/query",
    "/S9th0jAJ7bqgIRjw/arcgis/rest/services/C4S_Public_NoGO/FeatureServer/0/query",
    "/S9th0jAJ7bqgIRjw/arcgis/rest/services/C4S_Public_NoGO/FeatureServer/0/query",
    "/S9th0jAJ7bqgIRjw/arcgis/rest/services/C4S_Public_NoGO/FeatureServer/0",
  ]);
  for (const { url, init } of calls) {
    assert.equal(url.origin, "https://services.arcgis.com");
    assert.equal(url.searchParams.get("f"), "json");
    assert.equal(init.method, "GET");
    assert.equal(init.credentials, "omit");
    assert.equal(init.referrerPolicy, "no-referrer");
    assert.equal(init.redirect, "error");
    assert.equal(init.headers, undefined);
  }
  assert.equal(calls[1].url.searchParams.get("where"), selectedCallsPolicy.where);
  assert.equal(calls[2].url.searchParams.get("returnGeometry"), "false");
  assert.equal(calls[2].url.searchParams.get("outFields"), "DIVISION");
  assert.match(calls[2].url.searchParams.get("outStatistics"), /OBJECTID/);
  assert.match(state.disclosure, /not all crime/);
  assert.equal(state.attribution, "Contains information licensed under the Open Government Licence - Ontario.");
  assert.equal("features" in state, false);
  assert.equal("OBJECTID" in state, false);
});

test("does not request while hidden and aborts/clears counts when leaving the view", async () => {
  const first = harness();
  first.client.setVisible(false);
  assert.equal((await first.client.load()).status, "unavailable");
  assert.equal(first.calls.length, 0);
  first.client.setVisible(true);
  assert.equal((await first.client.load()).status, "available");
  first.client.setVisible(false);
  assert.equal(first.client.state().status, "unavailable");
  assert.deepEqual(first.client.state().counts, []);
});

test("upstream data older than 30 minutes fails closed with no counts", async () => {
  const h = harness({ beforeEdit: now0 - 30 * 60_000 - 1 });
  const result = await h.client.load();
  assert.equal(result.status, "unavailable");
  assert.deepEqual(result.counts, []);
  assert.equal(h.calls.length, 1);
});

test("generic layer edit does not make stale source data look fresh", async () => {
  const h = harness({
    beforeEdit: now0 - 1_000,
    afterEdit: now0 - 1_000,
    beforeDataEdit: now0 - 30 * 60_000 - 1,
    afterDataEdit: now0 - 30 * 60_000 - 1,
    beforeSchemaEdit: now0 - 60 * 60_000,
    afterSchemaEdit: now0 - 60 * 60_000,
  });
  assert.equal((await h.client.load()).status, "unavailable");
  assert.equal(h.calls.length, 1);
});

test("future source timestamps beyond tolerance fail closed", async () => {
  const h = harness({ beforeEdit: now0 + 60_001 });
  const result = await h.client.load();
  assert.equal(result.status, "unavailable");
  assert.deepEqual(result.counts, []);
});

test("source edit time and count must be unchanged across the request sequence", async () => {
  const metadataChange = harness({ afterEdit: edit0 + 1 });
  assert.equal((await metadataChange.client.load()).status, "unavailable");
  assert.deepEqual(metadataChange.client.state().counts, []);
  const countChange = harness({ countAfter: 17 });
  assert.equal((await countChange.client.load()).status, "unavailable");
  assert.deepEqual(countChange.client.state().counts, []);
  const schemaChange = harness({ afterMetadataPatch: { fields: [{ name: "OBJECTID", type: "esriFieldTypeOID" }, { name: "OTHER", type: "esriFieldTypeString" }] } });
  assert.equal((await schemaChange.client.load()).status, "unavailable");
  const badType = harness({ beforeMetadataPatch: { fields: [{ name: "OBJECTID", type: "esriFieldTypeString" }, { name: "DIVISION", type: "esriFieldTypeOID" }] } });
  assert.equal((await badType.client.load()).status, "unavailable");
  assert.equal(badType.calls.length, 1);
  const genericOnlyChange = harness({ afterEdit: edit0 + 2, afterDataEdit: edit0, afterSchemaEdit: edit0 });
  assert.equal((await genericOnlyChange.client.load()).status, "unavailable");
  const dataRevisionChange = harness({ afterEdit: edit0, afterDataEdit: edit0 + 1, afterSchemaEdit: edit0 });
  assert.equal((await dataRevisionChange.client.load()).status, "unavailable");
  const missingDataRevision = harness({ beforeMetadataPatch: { editingInfo: { lastEditDate: edit0, schemaLastEditDate: edit0 } } });
  assert.equal((await missingDataRevision.client.load()).status, "unavailable");
  const inconsistentRevision = harness({ beforeMetadataPatch: { editingInfo: { lastEditDate: edit0, dataLastEditDate: edit0 + 1, schemaLastEditDate: edit0 } } });
  assert.equal((await inconsistentRevision.client.load()).status, "unavailable");
});

test("duplicate, unknown, geometry-bearing, truncated and malformed groups fail closed", async (t) => {
  const cases = [
    ["duplicate", { groups: [["D41", 8], ["D41", 8]], count: 16 }],
    ["unknown division", { groups: [["D44", 16]], count: 16 }],
    ["transfer limit", { groupedPatch: { exceededTransferLimit: true } }],
    ["geometry", { groupedPatch: { features: [{ attributes: { DIVISION: "D41", call_count: 16 }, geometry: {} }] } }],
    ["extra attribute", { groupedPatch: { features: [{ attributes: { DIVISION: "D41", call_count: 16, OBJECTID: 1 } }] } }],
    ["bad JSON-shaped attributes", { groupedPatch: { features: [{ attributes: { DIVISION: "D41", call_count: "16" } }] } }],
    ["count mismatch", { groups: [["D41", 15]], count: 16 }],
  ];
  for (const [name, options] of cases) await t.test(name, async () => {
    const h = harness(options);
    const state = await h.client.load();
    assert.equal(state.status, "unavailable");
    assert.deepEqual(state.counts, []);
  });
  const presentFalse = harness({ groupedPatch: { exceededTransferLimit: false } });
  assert.equal((await presentFalse.client.load()).status, "available");
  const absentFlag = harness({ omitTransferFlag: true });
  assert.equal((await absentFlag.client.load()).status, "available");
  const invalidFlag = harness({ groupedPatch: { exceededTransferLimit: "false" } });
  assert.equal((await invalidFlag.client.load()).status, "unavailable");
});

test("a coherent empty source response is available as an empty count set", async () => {
  const h = harness({ groups: [], count: 0 });
  const state = await h.client.load();
  assert.equal(state.status, "available");
  assert.deepEqual(state.counts, []);
});

test("non-OK, redirect, wrong-host and oversized responses fail closed", async (t) => {
  await t.test("HTTP failure", async () => {
    const h = harness();
    h.client.fetchImpl = async () => new Response("", { status: 503 });
    const state = await h.client.load();
    assert.equal(state.status, "unavailable");
  });
  await t.test("redirected response", async () => {
    const h = harness();
    const base = h.client.fetchImpl;
    let first = true;
    h.client.fetchImpl = async (...args) => {
      if (first) { first = false; const r = await base(...args); Object.defineProperty(r, "redirected", { value: true }); return r; }
      return base(...args);
    };
    assert.equal((await h.client.load()).status, "unavailable");
  });
  await t.test("unexpected URL", async () => {
    const h = harness();
    h.client.fetchImpl = async (_requested, init) => ({
      ok: true, status: 200, redirected: false,
      url: "https://example.invalid/arcgis/rest/services/C4S_Public_NoGO/FeatureServer/0?f=json",
      headers: new Headers({ "content-type": "application/json" }),
      body: new Response(JSON.stringify(metadata())).body,
    });
    assert.equal((await h.client.load()).status, "unavailable");
  });
  await t.test("oversized response", async () => {
    const h = harness();
    h.client.limits = Object.freeze({ ...h.client.limits, maxResponseBytes: 10 });
    assert.equal((await h.client.load()).status, "unavailable");
  });
});

test("one in-flight request is shared and cooldown covers failures", async () => {
  const time = { wall: now0, mono: 1_000 };
  const transport = fixtureTransport();
  let releaseFirst;
  const gate = new Promise((resolve) => { releaseFirst = resolve; });
  const baseFetch = transport.fetchImpl;
  let blocked = false;
  const client = new SelectedCallsClient({
    fetchImpl: async (...args) => {
      if (!blocked) { blocked = true; await gate; }
      return baseFetch(...args);
    },
    now: () => time.wall,
    monotonicNow: () => time.mono,
  });
  client.setVisible(true);
  const first = client.load();
  const second = client.load();
  releaseFirst();
  assert.equal(await first, await second);
  assert.equal(transport.calls.length, 5);
  time.mono += 1_000;
  await client.load({ force: true });
  assert.equal(transport.calls.length, 5);
});

test("minimum retry interval applies after failed requests", async () => {
  const h = harness({ responseAt: 0 });
  assert.equal((await h.client.load()).status, "unavailable");
  assert.equal(h.calls.length, 1);
  h.time.mono += 1_000;
  assert.equal((await h.client.load({ force: true })).status, "unavailable");
  assert.equal(h.calls.length, 1);
});

test("leaving the view aborts the active request and prevents later stages", async () => {
  const time = { wall: now0, mono: 1_000 };
  let signal;
  let resolveFetch;
  const pending = new Promise((resolve) => { resolveFetch = resolve; });
  const client = new SelectedCallsClient({
    fetchImpl: async (_url, init) => {
      signal = init.signal;
      return pending;
    },
    now: () => time.wall,
    monotonicNow: () => time.mono,
  });
  client.setVisible(true);
  const loading = client.load();
  client.setVisible(false);
  assert.equal(signal.aborted, true);
  resolveFetch(new Response(JSON.stringify(metadata()), { status: 200 }));
  const result = await loading;
  assert.equal(result.status, "unavailable");
  assert.deepEqual(result.counts, []);
});

test("local cache expires after ten minutes and suspicious wall-clock changes hide counts", async (t) => {
  await t.test("local expiry", async () => {
    const h = harness();
    assert.equal((await h.client.load()).status, "available");
    h.time.mono += selectedCallsPolicy.maxLocalAgeMs + 1;
    h.time.wall += selectedCallsPolicy.maxLocalAgeMs + 1;
    assert.equal(h.client.state().status, "unavailable");
    assert.deepEqual(h.client.state().counts, []);
  });
  await t.test("wall clock jumps", async () => {
    const h = harness();
    assert.equal((await h.client.load()).status, "available");
    h.time.wall += 5 * 60_000;
    assert.equal(h.client.state().status, "unavailable");
    assert.deepEqual(h.client.state().counts, []);
  });
});

test("counts expire when the source reaches its 30-minute edit-age limit", async () => {
  const h = harness({ beforeEdit: now0 - 29 * 60_000, beforeDataEdit: now0 - 29 * 60_000, beforeSchemaEdit: now0 - 29 * 60_000 });
  assert.equal((await h.client.load()).status, "available");
  h.time.mono += 60_001;
  h.time.wall += 60_001;
  assert.equal(h.client.state().status, "unavailable");
  assert.deepEqual(h.client.state().counts, []);
});

test("source errors never retain previously displayed counts", async () => {
  const h = harness();
  assert.equal((await h.client.load()).status, "available");
  h.time.mono += selectedCallsPolicy.minAttemptIntervalMs;
  h.time.wall += selectedCallsPolicy.minAttemptIntervalMs;
  h.client.fetchImpl = async () => new Response(JSON.stringify({ error: { message: "synthetic error" } }), { status: 200 });
  const state = await h.client.load({ force: true });
  assert.equal(state.status, "unavailable");
  assert.deepEqual(state.counts, []);
  assert.deepEqual(h.client.state().counts, []);
});

