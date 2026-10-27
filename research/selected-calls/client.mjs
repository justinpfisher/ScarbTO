const SERVICE = "https://services.arcgis.com/S9th0jAJ7bqgIRjw/arcgis/rest/services/C4S_Public_NoGO/FeatureServer/0";
const QUERY = `${SERVICE}/query`;
const DIVISIONS = Object.freeze(["D41", "D42", "D43"]);
const WHERE = "DIVISION IN ('D41','D42','D43')";
const LIMITS = Object.freeze({
  maxResponseBytes: 128 * 1024,
  timeoutMs: 8_000,
  maxUpstreamAgeMs: 30 * 60_000,
  maxLocalAgeMs: 10 * 60_000,
  minAttemptIntervalMs: 5 * 60_000,
  futureClockToleranceMs: 60_000,
  clockDriftToleranceMs: 60_000,
});

const UNAVAILABLE = (reason) => Object.freeze({
  status: "unavailable",
  reason,
  label: "Selected calls published by TPS - Divisions 41, 42 and 43",
  counts: Object.freeze([]),
});

function fail(message) {
  throw new Error(message);
}

function exactKeys(value, expected, label) {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail(`${label} must be an object`);
  const actual = Object.keys(value).sort();
  const wanted = [...expected].sort();
  if (actual.length !== wanted.length || actual.some((key, i) => key !== wanted[i])) {
    fail(`${label} has unexpected fields`);
  }
}

function safeCount(value, label) {
  if (!Number.isSafeInteger(value) || value < 0) fail(`${label} must be a nonnegative safe integer`);
  return value;
}

function metadataEditTime(metadata) {
  if (!metadata || typeof metadata !== "object" || metadata.error) fail("invalid layer metadata");
  if (!Array.isArray(metadata.fields)) fail("layer metadata has no field list");
  const fields = new Map(metadata.fields.map((field) => [field?.name, field?.type]));
  if (fields.get("DIVISION") !== "esriFieldTypeString" || fields.get("OBJECTID") !== "esriFieldTypeOID") {
    fail("required aggregate fields have unexpected types");
  }
  const value = metadata.editingInfo?.lastEditDate;
  if (!Number.isSafeInteger(value) || value <= 0) fail("source edit time is unavailable");
  return value;
}

function metadataSignature(metadata) {
  return JSON.stringify({
    editTime: metadataEditTime(metadata),
    objectIdField: metadata.objectIdField ?? null,
    globalIdField: metadata.globalIdField ?? null,
    geometryType: metadata.geometryType ?? null,
    spatialReference: metadata.spatialReference
      ? { wkid: metadata.spatialReference.wkid ?? null, latestWkid: metadata.spatialReference.latestWkid ?? null }
      : null,
    fields: metadata.fields.map((field) => ({ name: field.name ?? null, type: field.type ?? null })),
  });
}

function countValue(payload, label) {
  if (!payload || typeof payload !== "object" || payload.error) fail(`${label} response is invalid`);
  return safeCount(payload.count, `${label} count`);
}

function groupedCounts(payload, controlCount) {
  if (!payload || typeof payload !== "object" || payload.error || !Array.isArray(payload.features)) {
    fail("grouped response is invalid");
  }
  if (payload.exceededTransferLimit === true) fail("grouped response was truncated");
  if (payload.exceededTransferLimit !== false) fail("grouped response omitted transfer-limit status");
  const found = new Map();
  for (const feature of payload.features) {
    if (Object.hasOwn(feature ?? {}, "geometry")) fail("grouped response included geometry");
    exactKeys(feature, ["attributes"], "group feature");
    exactKeys(feature.attributes, ["DIVISION", "call_count"], "group attributes");
    const division = feature.attributes.DIVISION;
    if (!DIVISIONS.includes(division)) fail("grouped response included an unknown division");
    if (found.has(division)) fail("grouped response included a duplicate division");
    found.set(division, safeCount(feature.attributes.call_count, "division count"));
  }
  const sum = [...found.values()].reduce((total, count) => total + count, 0);
  if (!Number.isSafeInteger(sum) || sum !== controlCount) fail("grouped counts do not match the control count");
  if (controlCount === 0 && found.size !== 0) fail("zero control count had nonzero groups");
  if (controlCount > 0 && found.size === 0) fail("nonzero control count had no groups");
  return DIVISIONS.filter((division) => found.has(division)).map((division) => Object.freeze({
    division,
    count: found.get(division),
  }));
}

function queryUrl(params) {
  const url = new URL(QUERY);
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, String(value));
  return url;
}

function makeRequests() {
  const where = { where: WHERE, f: "json", returnCountOnly: "true" };
  return [
    new URL(`${SERVICE}?f=json`),
    queryUrl(where),
    queryUrl({
      where: WHERE,
      f: "json",
      outFields: "DIVISION",
      returnGeometry: "false",
      groupByFieldsForStatistics: "DIVISION",
      orderByFields: "DIVISION",
      outStatistics: JSON.stringify([{
        statisticType: "count",
        onStatisticField: "OBJECTID",
        outStatisticFieldName: "call_count",
      }]),
    }),
    queryUrl(where),
    new URL(`${SERVICE}?f=json`),
  ];
}

async function readBoundedJson(response, expectedUrl, maxBytes) {
  if (!response || !response.ok) fail(`source returned HTTP ${response?.status ?? "unknown"}`);
  if (response.redirected) fail("source response redirected");
  if (response.url) {
    const finalUrl = new URL(response.url);
    if (finalUrl.href !== expectedUrl.href) {
      fail("source response came from an unexpected URL");
    }
  }
  const contentLength = response.headers?.get?.("content-length");
  if (contentLength !== null && contentLength !== undefined && /^\d+$/.test(contentLength) && Number(contentLength) > maxBytes) {
    fail("source response exceeded the byte limit");
  }

  let text;
  if (response.body?.getReader) {
    const reader = response.body.getReader();
    const chunks = [];
    let bytes = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        bytes += value.byteLength;
        if (bytes > maxBytes) {
          await reader.cancel();
          fail("source response exceeded the byte limit");
        }
        chunks.push(value);
      }
    } finally {
      reader.releaseLock?.();
    }
    const joined = new Uint8Array(bytes);
    let offset = 0;
    for (const chunk of chunks) {
      joined.set(chunk, offset);
      offset += chunk.byteLength;
    }
    text = new TextDecoder("utf-8", { fatal: true }).decode(joined);
  } else {
    text = await response.text();
    if (new TextEncoder().encode(text).byteLength > maxBytes) fail("source response exceeded the byte limit");
  }
  try {
    return JSON.parse(text);
  } catch {
    fail("source response was not valid JSON");
  }
}

function freshness(editTime, nowWall, maxAge, futureTolerance) {
  if (!Number.isFinite(nowWall) || !Number.isFinite(editTime)) fail("clock or source timestamp is invalid");
  const age = nowWall - editTime;
  if (age < -futureTolerance) fail("source timestamp is in the future");
  if (age > maxAge) fail("source data is stale");
  return Math.max(0, age);
}

export class SelectedCallsClient {
  constructor({
    fetchImpl = globalThis.fetch,
    now = () => Date.now(),
    monotonicNow = () => globalThis.performance.now(),
    limits = LIMITS,
  } = {}) {
    if (typeof fetchImpl !== "function") throw new TypeError("fetchImpl is required");
    this.fetchImpl = fetchImpl;
    this.now = now;
    this.monotonicNow = monotonicNow;
    this.limits = Object.freeze({ ...LIMITS, ...limits });
    this.visible = false;
    this.current = null;
    this.inFlight = null;
    this.controller = null;
    this.lastAttemptMono = null;
    this.invalidReason = null;
  }

  setVisible(visible) {
    this.visible = Boolean(visible);
    if (!this.visible) {
      this.controller?.abort();
      this.current = null;
      this.invalidReason = "view hidden";
    }
  }

  state() {
    if (!this.visible) return UNAVAILABLE("view hidden");
    if (!this.current) return UNAVAILABLE(this.invalidReason ?? "not loaded");
    const wallElapsed = this.now() - this.current.loadedAtWall;
    const monoElapsed = this.monotonicNow() - this.current.loadedAtMono;
    if (!Number.isFinite(wallElapsed) || !Number.isFinite(monoElapsed) || wallElapsed < 0 || monoElapsed < 0 ||
        Math.abs(wallElapsed - monoElapsed) > this.limits.clockDriftToleranceMs) {
      this.current = null;
      this.invalidReason = "clock changed; refresh required";
      return UNAVAILABLE(this.invalidReason);
    }
    if (monoElapsed > this.limits.maxLocalAgeMs) {
      this.current = null;
      this.invalidReason = "cached counts expired";
      return UNAVAILABLE(this.invalidReason);
    }
    return this.current.publicState;
  }

  async load({ force = false } = {}) {
    if (!this.visible) return UNAVAILABLE("view hidden");
    if (this.inFlight) return this.inFlight;
    const nowMono = this.monotonicNow();
    if (!force && this.current && this.state().status === "available") return this.current.publicState;
    if (this.lastAttemptMono !== null && nowMono - this.lastAttemptMono < this.limits.minAttemptIntervalMs) {
      const state = this.state();
      return state.status === "available" ? state : UNAVAILABLE("refresh cooldown active");
    }

    this.lastAttemptMono = nowMono;
    this.invalidReason = null;
    const controller = new AbortController();
    this.controller = controller;
    let timedOut = false;
    const timeout = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, this.limits.timeoutMs);
    const requests = makeRequests();
    const requestStartMono = this.monotonicNow();
    const requestStartWall = this.now();
    const run = async () => {
      try {
        const call = async (url) => {
          const response = await this.fetchImpl(url.href, {
            method: "GET",
            mode: "cors",
            credentials: "omit",
            referrerPolicy: "no-referrer",
            redirect: "error",
            signal: controller.signal,
          });
          return readBoundedJson(response, url, this.limits.maxResponseBytes);
        };

        const beforeMetadata = await call(requests[0]);
        const beforeSignature = metadataSignature(beforeMetadata);
        const beforeEdit = metadataEditTime(beforeMetadata);
        freshness(beforeEdit, this.now(), this.limits.maxUpstreamAgeMs, this.limits.futureClockToleranceMs);
        const beforeCount = countValue(await call(requests[1]), "initial control");
        const grouped = await call(requests[2]);
        const afterCount = countValue(await call(requests[3]), "final control");
        const afterMetadata = await call(requests[4]);
        const afterEdit = metadataEditTime(afterMetadata);
        if (beforeSignature !== metadataSignature(afterMetadata)) fail("source metadata changed during request");
        if (beforeCount !== afterCount) fail("source count changed during request");
        const completedAt = this.now();
        const finalEditAge = freshness(afterEdit, completedAt, this.limits.maxUpstreamAgeMs, this.limits.futureClockToleranceMs);
        const counts = groupedCounts(grouped, beforeCount);
        if (!this.visible || controller.signal.aborted) fail("view is no longer active");
        const publicState = Object.freeze({
          status: "available",
          label: "Selected calls published by TPS - Divisions 41, 42 and 43",
          counts: Object.freeze(counts),
          sourceEditedAt: new Date(beforeEdit).toISOString(),
          sourceAgeMsAtFetch: finalEditAge,
          fetchedAt: new Date(completedAt).toISOString(),
          attribution: "Contains information licensed under the Open Government Licence - Toronto.",
          sourceUrl: "https://experience.arcgis.com/experience/a22f5295933e48a5b0a4c90cd3c4cae1",
          disclosure: "These are selected calls published for Divisions 41, 42 and 43. They are not all crime, police activity, or officer presence.",
        });
        this.current = {
          publicState,
          loadedAtWall: requestStartWall,
          loadedAtMono: requestStartMono,
        };
        this.invalidReason = null;
        return publicState;
      } catch (error) {
        this.current = null;
        this.invalidReason = timedOut ? "source request timed out" : controller.signal.aborted ? "request cancelled" : "source data unavailable";
        return UNAVAILABLE(this.invalidReason);
      } finally {
        clearTimeout(timeout);
        if (this.controller === controller) this.controller = null;
        this.inFlight = null;
      }
    };
    this.inFlight = run();
    return this.inFlight;
  }
}

export const selectedCallsPolicy = Object.freeze({
  serviceUrl: SERVICE,
  divisions: DIVISIONS,
  where: WHERE,
  maxResponseBytes: LIMITS.maxResponseBytes,
  timeoutMs: LIMITS.timeoutMs,
  maxUpstreamAgeMs: LIMITS.maxUpstreamAgeMs,
  maxLocalAgeMs: LIMITS.maxLocalAgeMs,
  minAttemptIntervalMs: LIMITS.minAttemptIntervalMs,
});

