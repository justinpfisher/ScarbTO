const OFFICIAL_VIEW_URL =
  "https://www.toronto.ca/community-people/health-wellness-care/health-inspections-monitoring/swimsafe/beach-water-quality/";

const STATUS_MESSAGES = Object.freeze({
  out_of_season: "Water-quality testing is out of season. Check the official source for current information.",
  stale: "The latest beach information is stale; a current water-quality status is unavailable.",
  no_current_result: "No current water-quality result is available.",
  freshness_unknown: "The update time is unavailable, so a current status cannot be confirmed.",
  freshness_unqualified: "The update time has not been qualified for freshness, so no current status is shown.",
  season_state_unknown: "The current season state is unavailable, so no water-quality status is shown.",
  maintenance: "Toronto has temporarily marked the beach information service as under maintenance.",
  maintenance_state_unknown: "The maintenance state is unavailable, so no current status is shown.",
  status_unrecognized: "Toronto returned an unrecognized status; check the official source.",
  access_closed: "This beach has a separately reported access closure. Check the official notice.",
});

/** Create a text-only beach status card from the normalized adapter result.
 * The caller owns insertion and focus behavior. This module has no data fetch
 * or publication path and never renders measurements or coordinates.
 */
export function createBeachStatusCard(document, card) {
  const section = document.createElement("section");
  section.className = "layer-status beach-status";

  const heading = document.createElement("h3");
  heading.textContent = typeof card?.beach_name === "string" && card.beach_name.trim()
    ? card.beach_name.trim()
    : "Beach water quality";

  const message = document.createElement("p");
  if (card?.display_state === "current" && typeof card.water_quality_status === "string" && card.water_quality_status.trim()) {
    const labels = { safe: "Safe to swim", caution: "Caution is advised", unavailable: "Data unavailable" };
    message.textContent = `Official water-quality status: ${labels[card.water_quality_status] ?? "Unavailable"}`;
  } else {
    message.textContent = STATUS_MESSAGES[card?.display_state]
      ?? "Current water-quality information is unavailable.";
  }

  const source = document.createElement("a");
  source.href = OFFICIAL_VIEW_URL;
  source.target = "_blank";
  source.rel = "noopener noreferrer";
  source.textContent = "Open the official Toronto beach-status source";

  section.append(heading, message);
  if (typeof card?.advisory === "string" && card.advisory.trim()) {
    const advisory = document.createElement("p");
    advisory.className = "beach-advisory";
    advisory.textContent = card.advisory.trim();
    section.append(advisory);
  }
  section.append(source);
  return section;
}

