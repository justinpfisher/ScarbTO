import {currentCopy} from './scarb-current-copy.mjs';
import {SOURCE_TRANSLATIONS} from './inspection-translations.mjs';
/**
 * Approved Scarb-authored copy gateway. Pure and deterministic: no network,
 * runtime AI, source mutation or free-form factual rewriting.
 * See SCARB_VOICE_GATEWAY.md before adding a new public copy path.
 */
export const VOICE_REVISION = '2026-11-17-2x';

export const SCARB_COPY = Object.freeze({
  "app-audit-source": "Source",
  "app-audit-meaning": "Meaning",
  "evidence-audit-download": "Download original {{KIND}}",

  "app-audit-show-key": "Show map key",
  "app-audit-hide-key": "Hide map key",
  "app-audit-beach-label": "Beach samples",
  "app-audit-recent": "Recent changes",
  "app-audit-loading": "Loading",
  "app-audit-unavailable": "Unavailable",
  "app-audit-zero": "0 in view",
  "app-audit-clear": "Clear filters",
  "app-audit-fit": "Fit Scarborough",
  "app-audit-inspection-prefix": "Inspection: ",
  "app-audit-updated": "Updated",
  "app-audit-unknown": "unknown",
  "app-audit-hide-filters": "Hide filters",
  "app-audit-filters": "Filters",
  "exports-audit-map-limit": "Locations of included updates, not all places or current safety conditions.",
  "exports-audit-map-source": "City of Toronto boundaries and DineSafe. Open Government Licence - Toronto.",
  "exports-audit-map-receipt": "Scarb.TO | Retain the edition receipt for exact boundaries, dates and source records.",
  "embed-audit-coverage": ". Coverage: {{NAMES}}.",

  "event-prose-unavailable": "A reviewed explanation is not available for this update. The dated source facts and links remain available.",
  "event-nearby-coverage": "This update is in your selected nearby coverage, outside the core area.",
  "community-editor-message-01": "I could not load the qualified information. Please try again later.",
  "community-editor-message-02": "The receipt has an invalid public release reference.",
  "community-editor-message-03": "This receipt does not match its retained public source evidence. Do not reuse it as qualified information.",
  "community-editor-message-04": "The pinned boundary reference is unavailable.",
  "community-editor-message-05": "The receipt boundary differs from its pinned public definition.",
  "community-editor-message-06": "Previous exact information cut-off restored. Its printed copy stays unchanged.",
  "community-editor-message-07": "The boundary version changed. Your prior receipt and exact cut-off are retained. Choose current coverage explicitly; the next edition will explain the changed selection.",
  "community-editor-message-08": "Import the original finalised receipt first.",
  "community-editor-message-09": "Import the original finalised receipt before creating a revision.",
  "community-editor-message-10": "Explain what this revision changes.",
  "community-editor-message-11": "The revision explanation exceeds this copy limit. Increase the limit so it stays with the edition.",
  "community-editor-message-12": "Source-linked local updates from Scarb.TO",
  "community-editor-message-13": "Choose saved coverage",
  "community-editor-message-14": "Saved coverage restored as a separate publication. Import its finalised receipt to continue that publication, or choose an explicit first-edition start. No other publication cut-off is used.",
  "community-editor-message-15": "This saved coverage uses a changed boundary. Import its original receipt or choose current areas explicitly.",
  "community-editor-message-16": "Settings downloaded. This device already has 30 saved profiles; keep the portable file.",
  "community-editor-message-17": "Coverage saved on this device and downloaded for backup. No edition marker changed.",
  "community-editor-message-18": "Settings downloaded; browser storage is unavailable. Keep the file for another visit or device.",
  "community-editor-message-19": "The proof changed while exporting. Review and finalise the new proof.",
  "community-editor-message-20": "The proof changed while finalising. Review the new proof before proceeding.",
  "community-editor-message-21": "This package exceeds the 5 MB portable-receipt limit. Choose a smaller layout before finalising; your previous marker is unchanged.",
  "community-editor-message-22": "Your receipt downloaded, but this browser could not save it. Keep the file for your next edition.",
  "community-editor-message-23": "Finalised on this device. Keep the receipt with your exported copy; import it for the next edition.",
  "community-editor-message-24": "That receipt is too large. Choose a file under 5 MB.",
  "community-editor-message-25": "Settings restored as a separate publication. Import its finalised receipt to continue it, or choose an explicit first-edition start.",
  "community-editor-message-26": "The release reference is invalid.",
  "community-editor-message-27": "I could not restore the previous edition. Import its receipt or choose dates explicitly.",
  "community-editor-message-28": "The proof changed while exporting. Export the newly reviewed proof.",
  "community-publishing-message-01": "Words are whitespace-separated tokens. Characters are Unicode code points, including spaces, punctuation and LF newlines; text is NFC-normalised. Editorial counts include heading, body and qualifications. Panel counts also include sources.",
  "community-publishing-message-02": "Use an exact timestamp with a time zone.",
  "community-publishing-message-03": "A name or label is missing or invalid.",
  "community-publishing-message-04": "Choose a positive copy limit.",
  "community-publishing-message-05": "This settings file is not supported.",
  "community-publishing-message-06": "These settings include unsupported fields.",
  "community-publishing-message-07": "Choose up to 40 verified areas.",
  "community-publishing-message-08": "One selected boundary has not been verified.",
  "community-publishing-message-09": "Choose no more than 40 combined core and nearby areas.",
  "community-publishing-message-10": "Choose at least one core area.",
  "community-publishing-message-11": "Only qualified food inspection updates are available for publishing.",
  "community-publishing-message-12": "Choose a supported physical page size and margin.",
  "community-publishing-message-13": "Choose editorial or whole-panel limits.",
  "community-publishing-message-14": "Choose Polygon or MultiPolygon geometry.",
  "community-publishing-message-15": "Supply a non-empty list of boundary polygons within the publishing tool's polygon limit.",
  "community-publishing-message-16": "This boundary is too large for the publishing tool.",
  "community-publishing-message-17": "Boundary rings are missing.",
  "community-publishing-message-18": "Boundary rings must be closed.",
  "community-publishing-message-19": "Boundary coordinates must be longitude, latitude near Scarborough.",
  "community-publishing-message-20": "A boundary ring has no area.",
  "community-publishing-message-21": "A boundary ring crosses itself.",
  "community-publishing-message-22": "A hole must sit wholly inside its polygon.",
  "community-publishing-message-23": "Boundary holes must not overlap.",
  "community-publishing-message-24": "A source record is missing its identity.",
  "community-publishing-message-25": "Conflicting source records share one identity.",
  "community-publishing-message-26": "Choose a reporting end after the start, not in the future.",
  "community-publishing-message-27": "That period starts before the retained change history.",
  "community-publishing-message-28": "The qualified source release is unavailable.",
  "community-publishing-message-29": "I have no newer successful source check for that reporting period.",
  "community-publishing-message-30": "This limit cannot fit the reporting dates and essential qualifications. Increase the space or copy limit.",
  "community-publishing-message-31": "This limit leaves no room for one complete update. Increase it rather than dropping the qualifications.",
  "community-publishing-message-32": "The no-update explanation needs a larger copy limit.",
  "community-publishing-message-33": "Only a draft can be finalised.",
  "community-publishing-message-34": "Choose a finalised edition receipt.",
  "community-publishing-message-35": "This receipt has changed since it was finalised. Keep the original and create an explained revision.",
  "community-publishing-message-36": "This correction exceeds the revision limit or has an invalid original-edition link, revision sequence or explanation.",
  "community-publishing-message-37": "A correction requires a draft, and the original edition must remain below the revision limit.",
  "community-embed-message-01": "I could not load these updates. Follow the link below to explore Scarb.TO directly.",
  "community-embed-message-02": "This widget has an unsupported setting.",
  "community-embed-message-03": "Choose verified City areas in the community publishing tool first.",
  "community-embed-message-04": "Choose a reporting period from 1 to 365 days.",
  "community-embed-message-05": "The qualified release reference is unavailable.",
  "community-embed-message-06": "A selected boundary version changed. Open the publishing tool to review this coverage before updating the widget.",
  "community-embed-message-07": "The source projections disagree. These updates are unavailable.",
  "community-embed-message-08": "Official DineSafe source",
  "community-embed-message-09": "Open Government Licence - Toronto",
  "community-embed-message-10": "Pinned source evidence",
  "community-embed-message-11": "Last successfully checked ",
  "community-evidence-message-01": "Active map content is not supported.",
  "community-evidence-message-02": "The retained map is invalid.",
  "community-evidence-message-03": "External map paints are not supported.",
  "community-evidence-message-04": "The retained map path is unsupported.",
  "community-evidence-message-05": "The retained map font is unsupported.",
  "community-evidence-message-06": "Choose a receipt under 5 MB.",
  "community-evidence-message-07": "An original output hash does not match.",
  "community-exports-message-01": "Frozen, source-linked community edition",
  "community-exports-message-02": "The generated PNG is incomplete.",
  "beach-history-message-01": "Invalid beach-sample record",
  "beach-history-message-02": "None includes an E. coli number",
  "beach-history-message-03": "Sample records and sources",
  "beach-history-message-04": "No E. coli number was recorded",
  "beach-history-message-05": "See the City beach records",
  "beach-history-message-06": "Open Government Licence - Toronto",
  "beach-history-message-07": "Check current City swimming advice",
  "app-dynamic-01": "{{VALUE0}}: {{VALUE1}}",
  "app-dynamic-02": "TPS last changed these records {{VALUE0}}; checked {{VALUE1}}. Older counts are removed.",
  "app-dynamic-03": "Historical City samples through {{VALUE0}}. Not current swimming advice.",
  "app-dynamic-04": "{{VALUE0}} selected calls",
  "app-dynamic-05": "Division {{VALUE0}}",
  "app-dynamic-06": "{{VALUE0}} sample records",
  "app-dynamic-07": "I could not load the published records ({{VALUE0}}). The update history below may have more detail.",
  "app-dynamic-08": "{{VALUE0}} records in view",
  "app-dynamic-09": "Changed from {{VALUE0}}",
  "app-dynamic-10": "This source record ID: {{VALUE0}}",
  "app-dynamic-11": "{{VALUE0}}: {{VALUE1}}, inspected {{VALUE2}} (ID {{VALUE3}})",
  "app-dynamic-12": "Show next {{VALUE0}} matches",
  "app-dynamic-13": "These food inspection records may be out of date. Last checked {{VALUE0}}. Check the City's record for anything newer.",
  "app-dynamic-14": "Food inspection records checked {{VALUE0}}. These aren't live results.",
  "neighbourhood-page-dynamic-01": "Ward {{VALUE0}} — {{VALUE1}}: Find your City councillor",
  "neighbourhood-page-dynamic-02": "Inspected {{VALUE0}}",
  "neighbourhood-page-dynamic-03": "City record {{VALUE0}}: {{VALUE1}}, inspected {{VALUE2}}",
  "neighbourhood-page-dynamic-04": "Showing {{VALUE0}} of {{VALUE1}} DineSafe source records matched to this neighbourhood.",
  "neighbourhood-page-dynamic-05": "{{VALUE0}} · Scarb.TO",
  "neighbourhood-page-dynamic-06": "These results may be out of date. Last checked {{VALUE0}}. Check the City's record for anything newer.",
  "neighbourhood-page-dynamic-07": "Food inspection records checked {{VALUE0}}. These aren't live results.",
  "neighbourhood-page-dynamic-08": "Scarb.TO successful check: {{VALUE0}}. City catalogue timestamp: {{VALUE1}} (source timezone unspecified). These are separate from each inspection date and do not establish current conditions.",
  "community-evidence-dynamic-01": "{{VALUE0}}: {{VALUE1}}. Inspection {{VALUE2}}; first recorded {{VALUE3}}. Event {{VALUE4}}.",
  "community-evidence-dynamic-02": "Pinned information checked {{VALUE0}}. These are dated inspection outcomes, not conditions today.",
  "community-editor-dynamic-01": "Edition revision {{VALUE0}}.",
  "community-editor-dynamic-02": "\nPublisher's revision explanation: {{VALUE0}}",
  "community-editor-dynamic-03": "Editorial: {{VALUE0}} words, {{VALUE1}} characters. Sources: {{VALUE2}} words. Whole panel: {{VALUE3}} words, {{VALUE4}} characters.",
  "community-editor-dynamic-04": "Proof prepared from {{VALUE0}} eligible updates. {{VALUE1}} omitted for space. Review it before finalising.",
  "community-editor-dynamic-05": "Exported {{VALUE0}} by {{VALUE1}} mm. The image alternative is {{VALUE2}} pixels at 300 dpi. Review the actual file before finalising.",
  "community-embed-dynamic-01": "I have no successfully checked information for this rolling period. Last checked {{VALUE0}}. That does not mean nothing happened; the pinned evidence below retains the last qualified information.",
  "logic-01": "The City has not supplied a catalogue refresh time",
  "logic-02": "The City has not supplied a usable catalogue date",
  "beach-history-01": "These are older water samples, not today’s swimming conditions. Check the City’s latest advice before swimming.",
  "selected-calls-01": "Selected calls published by TPS - Divisions 41, 42 and 43",
  "selected-calls-02": "Selected calls published by Toronto Police Service for Divisions 41, 42 and 43. These are not all calls, crime, police activity or officer presence.",
  "selected-calls-03": "Checking police call totals for Divisions 41, 42 and 43.",
  "selected-calls-04": "Open this view to check police call totals for Divisions 41, 42 and 43.",
  "selected-calls-05": "Counts are removed when you leave this view. Open it again to check for fresh totals.",
  "selected-calls-06": "The TPS records are more than 30 minutes old, so no counts are shown.",
  "selected-calls-07": "The TPS records are now more than 30 minutes old. Older counts have been removed.",
  "selected-calls-08": "These counts have been here for more than 10 minutes and have expired. Check again for fresh totals.",
  "selected-calls-09": "The request to TPS did not finish within 8 seconds. No counts are shown.",
  "selected-calls-10": "The check was cancelled. No counts are shown.",
  "selected-calls-11": "Checks are at least 5 minutes apart. Please wait before checking again; no older counts are shown.",
  "selected-calls-12": "TPS changed the records while I was checking them, so no totals are shown.",
  "selected-calls-13": "The clock changed while these counts were open. I removed them because I cannot verify their age.",
  "selected-calls-14": "I could not verify the age of the TPS records, so no counts are shown.",
  "selected-calls-15": "I could not verify the TPS totals against the source checks, so no counts are shown.",
  "selected-calls-16": "The TPS request did not return a usable response. No counts are shown.",
  "selected-calls-17": "This browser could not retrieve the TPS totals. No counts are shown.",
  "selected-calls-18": "I could not verify the TPS totals, so no counts are shown.",
  "selected-calls-19": "Contains information licensed under the Open Government Licence - Ontario.",
  "selected-calls-20": "These are the selected calls TPS publishes for Divisions 41, 42 and 43, not all crime, police activity, or officer presence.",
  "neighbourhood-page-01": "Other source records with this name and address",
  "neighbourhood-page-02": "The source IDs differ. A matching name and address does not prove these are the same business, so I keep each record separate.",
  "neighbourhood-page-03": "I didn't find any DineSafe records with source coordinates in this neighbourhood. That doesn't mean there are no food businesses here.",
  "neighbourhood-page-04": "I couldn't find this neighbourhood page. Choose a neighbourhood from the Scarb.TO map instead.",
  "neighbourhood-page-05": "I couldn't load the food inspection results. That doesn't mean there are no records here. Try again or check the City's DineSafe data below.",
  "community-evidence-01": "The retained map contains unsupported active content.",
  "community-evidence-02": "The retained map has unsupported attributes.",
  "community-evidence-03": "Open the exact evidence link printed in your edition, or import its receipt.",
  "community-evidence-04": "I could not load that retained release. Your downloaded receipt also contains its supporting evidence.",
  "community-evidence-05": "The source release identity does not match.",
  "community-evidence-06": "This receipt belongs to a different source release. Open its exact evidence link.",
  "community-evidence-07": "An output format in this receipt is unsupported.",
  "community-evidence-08": "The receipt hash matches its retained copy and evidence. This detects changes, not organisational identity or approval.",
  "community-exports-01": "The licensed export font could not load. Try again before exporting.",
  "community-exports-02": "This update needs more page space to stay readable. Try a larger page or fewer updates; the source details need to stay legible.",
  "community-exports-03": "Image export is unavailable in this browser.",
  "community-exports-04": "The image font wraps differently at this size. Choose a wider layout before exporting.",
  "community-exports-05": "The high-resolution image could not be created.",
  "community-exports-06": "Selected coverage and locations of updates included in this edition",
  "app-01": "Loading the City records.",
  "app-02": "Loading selected TPS call counts for Divisions 41, 42 and 43.",
  "app-03": "Toronto Police Service selected calls, Divisions 41, 42 and 43. These are not all calls, confirmed crimes or neighbourhood incidents.",
  "app-04": "Source last changed",
  "app-05": "Successfully checked",
  "app-06": "Loading the historical beach samples.",
  "app-07": "City sample records checked",
  "app-08": "Latest sample date",
  "app-09": "I could not load the historical beach samples. They are not current swimming advice.",
  "app-10": "City of Toronto DineSafe Open Data",
  "app-11": "Scarb.TO successful check",
  "app-12": "City catalogue timestamp (source timezone unspecified)",
  "app-13": "The check time is not the inspection time or evidence of a new City update. Results describe the dated inspection, not current conditions.",
  "app-14": "Map background only; selected calls are not mapped individually",
  "app-15": "Map showing the beach reference point, not the individual sampling locations",
  "app-16": "Interactive map of places with DineSafe records. Shapes and letters identify inspection outcomes alongside colour. Each outcome is written out in the matching list.",
  "app-17": "Interactive map of places with DineSafe records. Letters identify inspection outcomes alongside colour. Each outcome is written out in the matching list.",
  "app-18": "Toronto Police Service · counts when you open this view",
  "app-19": "Police calls by division",
  "app-20": "These are selected calls published by TPS, not all crime, police activity, or officer presence. Opening this view asks TPS/Esri for division totals only. I do not request or map individual calls or locations.",
  "app-21": "Toronto Open Data · dated samples",
  "app-22": "A different kind of paper trail: historical water samples from the City catalogue. Compare their collection dates and measurements, but do not use them as current swimming advice.",
  "app-23": "Official inspections",
  "app-24": "Places to explore",
  "app-25": "Start with a place you know. I have linked its map point and dated records so you can follow the trail either way; your filters work in both.",
  "app-26": "Added to Scarb.TO",
  "app-27": "Latest City inspection records",
  "app-28": "Places with DineSafe records",
  "app-29": "Recently inspected",
  "app-30": "This is where the records get interesting: compare them from day to day and the changes come into view. Here’s what I found in DineSafe. The inspection date may be earlier than when a record first appeared here.",
  "app-31": "Here’s another way into the records: places with recent inspection dates. That doesn’t mean their records are new; check the City’s record for current details.",
  "app-32": "Pick a familiar name and follow its inspection trail with me. These are the latest DineSafe records in this snapshot, with the original City link beside each one.",
  "app-33": "Contains information licensed under the Open Government Licence – Ontario.",
  "app-34": "See the TPS selected-calls map",
  "app-35": "Loading the historical City beach samples.",
  "app-36": "I could not load the historical City beach samples.",
  "app-37": "See the City beach records",
  "app-38": "Loading the City records checked for Scarb.TO.",
  "app-39": "There are no checked DineSafe records here yet. Places will appear once the first set is ready.",
  "app-40": "No places match this view. There is more to explore: try fewer filters or show all of Scarborough. Missing results do not mean nothing has happened here.",
  "app-41": "Address unavailable",
  "app-42": "New inspection recorded",
  "app-43": "Added to Scarb.TO: ",
  "app-44": "Similar names in the source",
  "app-45": "Other source records have this name and address. Their IDs differ, so I have kept them separate. This is not proof that they are the same business.",
  "app-46": "See the City DineSafe record",
  "app-47": "The map could not load, but you can keep exploring. Search, filter and open the source records in the list below.",
  "app-48": "The map could not load, but your filters still work on the list.",
  "app-49": "Waiting for the first checked City records",
  "app-50": "I could not load the City records. No DineSafe results are shown.",
  "saved-unreadable": "I could not read your saved areas. You can still choose any area to explore.",
  "saved-write-failed": "This browser could not save the change. Your list has not changed.",
  "saved-wards": "City wards",
  "saved-neighbourhoods": "Neighbourhoods",
  "saved-remove": "Remove",
  "saved-remove-label": "Remove {{NAME}} from saved areas",
  "saved-removed": "Removed {{NAME}} from this browser.",
  "saved-duplicate": "{{NAME}} is already saved.",
  "saved-added": "Saved {{NAME}} on this browser.",
  "area-choice": "Choose an area",
  "area-results": "Food inspection results",
  "area-unavailable": "I could not load checked DineSafe records, so no record count is shown.",
  "area-inspection-limit": "These are the latest inspections in the records I have, not a live list of every restaurant.",
  "area-coordinate-limit": "I match source coordinates to City boundary polygons. Coordinates can be imperfect; this is not an independent address check. Different source IDs remain separate records, even when names and addresses match.",
  "area-stale": "These records may be out of date. Check the City record before relying on them.",
  "area-topic-limit": "This area filters DineSafe places only. Police division totals and historical beach samples cover different areas.",
  "area-office-title": "City councillor",
  "area-your-office-title": "Your City councillor",
  "area-office-link": "City profile and contact details",
  "area-office-date": "I checked this officeholder information on Saturday, October 31, 2026. The City profile is the place to confirm any changes.",
  "area-overlap": "Here is one of the map details I love following: a neighbourhood can cross ward lines. These wards overlap this neighbourhood on the City map. That tells us about boundaries, not how many residents live in each ward or whether a whole neighbourhood belongs to each one.",
  "area-membership": "I include 30 whole City neighbourhoods with most of their land area in Scarborough. The City does not assign them to a Scarborough district in this dataset. DineSafe places follow a separate rule: they must lie within the six Scarborough wards.",
  "area-page-title": "Neighbourhood page",
  "area-page-intro": "Keep this patch of Scarborough in view: its neighbourhood page brings the map, dated records and boundary sources together. Pick a familiar place and follow its paper trail.",
  "area-ridings-title": "Provincial & federal representatives",
  "area-ridings": "There is another set of boundaries to explore: provincial and federal ridings. They differ from City wards and neighbourhoods, so use your address to find the right MPP or MP.",
  "area-mpp": "Find your Ontario MPP",
  "area-mp": "Find your federal riding",
  "area-crime-title": "Historical crime",
  "area-ward-crime": "There is no ward crime total here. TPS reports whole-neighbourhood quarterly summaries; dividing those up between wards would give a misleading number.",
  "area-neighbourhood-crime": "The quarterly TPS neighbourhood summaries are not ready to publish here. I do not show incident locations or current crime counts.",
  "area-development-title": "Development & permits",
  "area-development": "Planning applications and issued permits tell you different things. I have not finished checking these sources for Scarb.TO, so I am not showing them or making claims about construction. You can still look up applications with the City.",
  "area-planning-link": "City planning application information",
  "area-boundary-title": "Boundary source",
  "area-boundary-licence": "These boundaries come from the City of Toronto, under the Open Government Licence - Toronto.",
  "area-boundary-link": "See the City boundary records",
  "area-ward-address": "Confirm your City ward by address",
  "area-other-topic": "These boundaries and area filters work with DineSafe places only. Police division totals and beach samples cover different areas.",
  "area-off": "Boundaries are off and the map-selected area is cleared. Your other filters stay in place.",
  "area-switched": "I cleared the previous map-selected area when you switched boundary types. Your other filters stay in place. Choose a new area for the map and list.",
  "area-boundary-missing": "I could not find a usable boundary for this area.",
  "area-boundary-failed": "The City boundary could not load. Your area filter is still in place.",
  "area-hidden": "Boundaries are hidden for this view. Police division totals and historical beach samples do not describe whole neighbourhoods or wards.",
  "home-title": "Scarborough has a lot of stories hiding in its data.",
  "home-intro": "Scarborough's maps and public records give me plenty to get curious about. I've brought the places, inspection results and neighbourhood boundaries together here, with their dates and sources. Pick a thread. Let's see where it leads.",
  "home-boundaries": "Here's a favourite Scarborough map quirk: City wards and neighbourhoods don't always line up. Try either boundary to narrow the food inspection map and list. Beach samples and police division totals use different areas.",
  "neighbourhood-intro": "Now this is a patch of Scarborough worth getting to know. I've put the food inspection records and City neighbourhood boundaries for {{NAME}} side by side. Start with a familiar place, then follow the source links. There's often another detail worth checking.",
  "directory-intro": "Malvern West is in the directory. So is Agincourt South-Malvern West. I know it\u2019s only a name on a list, but now I want both maps open. There are {{COUNT}} pages here, with names from the City of Toronto\u2019s neighbourhood registry. Scarb.TO chose which ones to include. It\u2019s not the City\u2019s official list of Scarborough neighbourhoods, and it doesn\u2019t tell you what an inspection would find today.",
  "community-title": "Let's turn local records into a neighbourhood update.",
  "community-intro": "There's a lot tucked away in Scarborough's public records. Choose your patch and I'll bring the dated, source-linked findings together for print or your website. The evidence stays attached; you decide what to share.",
  "community-coverage": "A little map nerdiness before we begin: City neighbourhoods don't always stay inside Scarborough's six ward boundaries. For DineSafe, I count only records inside those wards, even if a selected neighbourhood carries on beyond them. These are editorial selections, not claimed newspaper or association territories.",
  "community-core": "Your corner of Scarborough",
  "evidence-title": "Let's follow the paper trail.",
  "evidence-intro": "Now for one of my favourite parts: where did this edition's information actually come from? Here's the saved source release, its dates and what those records can tell us. This page doesn't publicly store a publisher's own wording; import the finalised receipt to inspect the exact edition.",
  "embed-title": "Local discoveries, with the receipts.",
  "embed-intro": "Here's what the records turned up for this area. I keep the source dates and links close by, because the trail behind a finding can be just as interesting as the finding itself.",
  "briefs-title": "The week's food inspection paper trail.",
  "briefs-intro": "I love seeing how one week's DineSafe records fit together. Pick an edition and follow the inspection dates, neighbourhood connections and original source links. A quiet week in these records isn't proof that nothing happened, and I only publish a brief when there are updates to share.",
  "editor-start": "Choose your neighbourhoods and reporting dates. Experiment with drafts all you like: your next edition starts after the last one you finalised, not after a preview or text download.",
  "missing-pdf-tools": "The PDF tools didn't load. You can still save the text and settings before reloading to try again; a finalised receipt is available only after finalisation succeeds.",
  "finding-explanation-fb4d5d15fe5e5507": "Utensils were not cleaned as often as needed.",
  "finding-explanation-166112e70da21005": "Waste was not collected when needed to keep the premises sanitary.",
  "finding-explanation-7155e6e6c00df05f": "The premises had not ensured that a food handler or supervisor completed the required food-handling training.",
  "finding-explanation-0baa6b9f81867a50": "Equipment surfaces were not cleaned as required.",
  "finding-explanation-d1a54a8320e2699e": "Equipment surfaces were not sanitized as required.",
  "finding-explanation-990b53cbf14a721e": "Surfaces in the premises were not cleaned as required.",
  "finding-explanation-250836a55400e2d2": "Surfaces in the premises were not sanitized as required.",
  "finding-explanation-0cccdf046fd4e2e1": "The inspection found a failure to ensure that food handlers practised good personal hygiene.",
  "finding-explanation-1af905522aa2a33f": "The inspection found a failure to ensure that food handlers protected against contamination by hair.",
  "finding-explanation-102fa7236342db38": "A food handler was not wearing clean outer clothing.",
  "finding-explanation-9ee635f015842859": "The premises had not ensured that a food handler or supervisor was present throughout the operating hours.",
  "finding-explanation-f882cb7b45e3af65": "Handwashing stations were not properly maintained with liquid soap and paper towels.",
  "finding-explanation-be850ff3201189da": "The ventilation system was not maintained to remove smoke.",
  "finding-explanation-e4aa7550e59bc4b0": "Inspection results were not posted as the inspector requested.",
  "finding-explanation-0ac7faf6108da739": "The most recent food safety inspection report or reports were not produced when required.",
  "finding-explanation-a453f43f952c3107": "The premises were not adequately protected against pests breeding.",
  "finding-explanation-b5624e0779fc3f7c": "The premises were not adequately protected against pests getting in.",
  "finding-explanation-7ea38bf0b6710acb": "The premises were not adequately protected against pests sheltering there.",
  "finding-explanation-376035dc95fc05a1": "Food was not adequately protected from contamination or adulteration. This does not establish that contamination occurred.",
  "finding-explanation-55b1373fe438a221": "There were not enough handwashing stations.",
  "finding-explanation-2fc75dccd864addb": "The required lighting was not provided throughout the operating hours.",
  "finding-explanation-8c997947787a0cee": "Equipment used to keep food hot did not have the required thermometer.",
  "finding-explanation-71163b5e8ba09bb7": "Refrigeration equipment did not have the required thermometer.",
  "finding-explanation-f47febd1613c1fbb": "Garbage was not removed when needed to keep the premises sanitary.",
  "finding-explanation-6d4e8868216f592c": "Waste was not removed when needed to keep the premises sanitary.",
  "finding-explanation-549749191cc32f62": "Conditions at the premises could adversely affect the food. This finding does not establish that contamination or illness occurred.",
  "finding-explanation-49cb0402e13be124": "Conditions at the premises could allow single-use containers to become contaminated. This finding does not establish that contamination occurred.",
  "finding-explanation-e9be03fc092ac361": "Equipment not regularly used was being kept in a food-handling room.",
  "finding-explanation-aa1edc84017fdbca": "Materials not regularly used were being kept in a food-handling room.",
  "finding-explanation-97881a45d10a023d": "The premises were not maintained so that the ceilings could be cleaned.",
  "finding-explanation-e929a3db8cf382f3": "The premises were not maintained so that the walls could be cleaned.",
  "finding-explanation-c99c97cd13926bfb": "The premises were not maintained so that the ceilings could be kept sanitary.",
  "finding-explanation-664e0ed0696a1822": "The premises were not maintained so that the walls could be kept sanitary.",
  "finding-explanation-3fa8b60a24dfb615": "Ceilings in a food-handling room were not in good repair.",
  "finding-explanation-60f58672d67dea9b": "The ceiling in a food-handling room was not clean.",
  "finding-explanation-9ffe7b3753d0a052": "Floors in a food-handling room were not clean.",
  "finding-explanation-e6a840398ac06901": "Walls in a food-handling room were not clean.",
  "finding-explanation-233b3a3934b6fc0d": "Floors in a food-handling room were not in good repair.",
  "finding-explanation-f9eb75190a51c30d": "A food-handling room was not kept sanitary.",
  "finding-explanation-890e0fb1977b8965": "The floor surface where food was handled was not non-absorbent as required.",
  "finding-explanation-544b08c684a7ba77": "The floor surface where food was handled was not smooth as required.",
  "finding-explanation-4ff4bb2e488f0940": "The floor surface where utensils were cleaned was not smooth as required.",
  "finding-explanation-43d5b22e576e6a48": "The floor surface where food was handled was not tightly fitted as required.",
  "finding-explanation-48e8c6a0de01d3df": "The floor surface where utensils were cleaned was not tightly fitted as required.",
  "finding-explanation-0bd1898c410b80ab": "Walls in a food-handling room were not in good repair.",
  "finding-explanation-9f0584588789d2f6": "Food handlers could not conveniently reach the handwashing stations.",
  "finding-explanation-3c52d9cf17d280b1": "No licence was available at the inspection. The matter was referred to Municipal Licensing and Standards. This does not establish that the business had no licence.",
  "finding-explanation-3be26fcb2bea0ad3": "Appliances were not built in a way that allowed them to be cleaned.",
  "finding-explanation-c17bbbf70409c000": "Appliances were not built in a way that allowed them to be kept sanitary.",
  "finding-explanation-e30d88d467d25736": "Equipment was not arranged in a way that allowed it to be cleaned.",
  "finding-explanation-956d3f8b5784c964": "Equipment was not arranged in a way that allowed it to be kept sanitary.",
  "finding-explanation-d06c0b1ad56687b4": "Equipment was not built in a way that allowed it to be cleaned.",
  "finding-explanation-88eeb889ed6c8232": "Equipment was not built in a way that allowed it to be kept sanitary.",
  "finding-explanation-40a5c4ce267befac": "The washroom did not have single-use towels or a dryer as required.",
  "finding-explanation-c81e84fecdde1720": "The washroom did not have soap or detergent as required.",
  "finding-explanation-2a5a4167ff430b78": "The washroom did not have toilet paper as required.",
  "finding-explanation-f9ae482f2342e759": "The washroom was not kept in good repair.",
  "finding-explanation-301b33152fa2ae4e": "The washroom was not kept sanitary.",
  "finding-explanation-982425a3e677e82b": "Furniture was not arranged in a way that allowed it to be kept sanitary.",
  "finding-explanation-f1c3821f2efad5f0": "Furniture was not built in a way that allowed it to be cleaned.",
  "finding-explanation-81cb5ba276533b89": "Furniture was not built in a way that allowed it to be kept sanitary.",
  "finding-explanation-a1d039c638d480c8": "The mechanical washing equipment was not maintained to keep rinse water at 82°C.",
  "finding-explanation-311c575d18c08f88": "The mechanical washing equipment was not maintained to keep rinse water at 82°C.",
  "finding-explanation-2fa203d49f248dbf": "The mechanical washing equipment was not maintained to supply clean wash water.",
  "finding-explanation-99e18a7c0db2be70": "The mechanical washing equipment was not maintained to provide a sufficient chemical-solution rinse.",
  "finding-explanation-1eaa43e01db597ad": "The rinse-water thermometer was not easy to read.",
  "finding-explanation-bc87fa104f07ca31": "The mobile food premises did not have a gauge on the waste tank.",
  "finding-explanation-4687388b4399098f": "The chlorine solution used to sanitize utensils contained less than 100 parts per million of available chlorine.",
  "finding-explanation-0d7b4ce606acee55": "The quaternary ammonium solution used to sanitize utensils contained less than 200 parts per million.",
  "finding-explanation-453b1dae8806a855": "Utensils were sanitized using an agent for which the testing reagent was not readily available.",
  "finding-explanation-3b80f2b85f700014": "The thermometer in equipment used to keep food hot was not easy to read.",
  "finding-explanation-c484c25ea66993ed": "The thermometer in refrigeration equipment was not easy to read.",
  "finding-explanation-a0d4bd970117a106": "Equipment was being used for a purpose it was not suitable for.",
  "finding-explanation-7507fe18e4efce30": "Food equipment being used was not designed so it could be readily cleaned.",
  "finding-explanation-54a68a5e7db206d7": "Food equipment being used was not made of material that could be readily cleaned.",
  "finding-explanation-fcf37504d73b4996": "Food equipment being used was not of sound, tight construction.",
  "finding-explanation-2c28027af8513b95": "Multi-service articles that were not readily cleanable were being used.",
  "finding-explanation-e515079639b0b2ad": "Reusable articles were being used for a purpose they were not suitable for.",
  "finding-explanation-c4fbfa3a08039d7c": "Equipment in contact with food was not corrosion-resistant.",
  "finding-explanation-ff5650b4f3e1d752": "Utensils in contact with food were not corrosion-resistant.",
  "finding-explanation-55eb3a9acbeba3d6": "Shelves being used were not designed so they could be readily cleaned.",
  "finding-explanation-4586d24a972736ff": "A towel used for another purpose was also used to clean a food-contact surface.",
  "finding-explanation-2f130e4ac268594b": "Cracked utensils were used in contact with food.",
  "finding-explanation-09a869a514276b26": "Utensils being used were not in good repair.",
  "finding-explanation-20363154ac4a238b": "Utensils used in contact with food did not meet the non-toxic-material requirement. This finding does not establish that poisoning occurred.",
  "finding-explanation-496fe84fd1aa10a6": "Utensils being used were not designed so they could be readily cleaned.",
  "finding-explanation-dc61761581abe33d": "Utensils being used were not made of material that could be readily cleaned.",
  "finding-explanation-ffc9683a1081a818": "Utensils being used were not of sound, tight construction.",
  "finding-explanation-5072e77f0a9cf64c": "Utensils were being used for a purpose they were not suitable for.",
  "finding-explanation-7e0c1202c0f59cfd": "Food requiring temperature control was held at an internal temperature between 4°C and 60°C.",
  "composition-heading": "Here's what turned up in the DineSafe records for {{NAME}}",
  "composition-footer": "Edition revision 1. Information cut-off: {{CUTOFF}}.\nCity of Toronto DineSafe: https://open.toronto.ca/dataset/dinesafe/\nOpen Government Licence - Toronto: https://open.toronto.ca/open-data-licence/\nInformation checked {{CHECKED}}. Evidence: https://scarb.to/community/evidence/?release={{RELEASEID}}\nPrepared with Scarb.TO. Keep the downloaded receipt with this edition. Scarb.TO's editorial voice is AI-assisted, not first-hand reporting.",
  "composition-limitations": "One detail I never want to skip: these dated inspection results are not restaurant ratings or a guarantee of conditions today. Check the official DineSafe record for anything newer.",
  "composition-stale": "I couldn't check for anything newer than {{CHECKED}}. This edition does not cover later information.",
  "composition-changed": "The selected areas or settings changed since the previous edition. That makes this a different view of the records, not a like-for-like comparison.",
  "composition-snapshot": "Here's a useful bit of context: this selection contains {{COUNT}} DineSafe establishment source records from the snapshot checked {{CHECKED}}. That's not the number of changes during this period, or necessarily the number of distinct businesses.",
  "composition-empty": "Well, this is interesting in its own quiet way: I found no new updates in the DineSafe records checked for these areas and dates. That doesn't mean nothing happened. The source dates above show exactly what I checked.",
  "composition-period-inclusive": "Here's the time window I checked: information added from {{START}} through {{END}}. The inspections themselves may have happened earlier; I show each inspection date separately.",
  "composition-period-exclusive": "Here's the time window I checked: information added after {{START}} through {{END}}. The inspections themselves may have happened earlier; I show each inspection date separately.",
  "composition-event-first_seen": "{{NAME}} appeared in the records I checked for the first time (not a confirmed opening). DineSafe recorded {{STATUS}} for the inspection on {{INSPECTED}}. Scarb.TO first recorded this information on {{RECORDED}}.",
  "composition-event-first_seen-nearby": "From nearby: {{NAME}} appeared in the records I checked for the first time (not a confirmed opening). DineSafe recorded {{STATUS}} for the inspection on {{INSPECTED}}. Scarb.TO first recorded this information on {{RECORDED}}.",
  "composition-event-status_changed": "A change worth checking in the original record: {{NAME}} moved from a recorded {{PREVIOUS}} to {{STATUS}}. DineSafe recorded {{STATUS}} for the inspection on {{INSPECTED}}. Scarb.TO first recorded this information on {{RECORDED}}.",
  "composition-event-status_changed-nearby": "From nearby: A change worth checking in the original record: {{NAME}} moved from a recorded {{PREVIOUS}} to {{STATUS}}. DineSafe recorded {{STATUS}} for the inspection on {{INSPECTED}}. Scarb.TO first recorded this information on {{RECORDED}}.",
  "composition-event-new_inspection": "Another dated inspection update turned up for {{NAME}}. DineSafe recorded {{STATUS}} for the inspection on {{INSPECTED}}. Scarb.TO first recorded this information on {{RECORDED}}.",
  "composition-event-new_inspection-nearby": "From nearby: Another dated inspection update turned up for {{NAME}}. DineSafe recorded {{STATUS}} for the inspection on {{INSPECTED}}. Scarb.TO first recorded this information on {{RECORDED}}.",
  "composition-boundary-standard": "Here's an interesting boundary wrinkle: some neighbourhoods cross Scarborough's six City ward lines. I count only DineSafe records inside those wards, so this may be a slice of a neighbourhood, not its whole total.",
  "composition-boundary-other": "A boundary detail worth keeping in view: {{NOTE}}",
  "composition-embed-all": "{{SHOWN}} dated updates shown from {{ELIGIBLE}} eligible records. Here's the boundary wrinkle: DineSafe coverage is limited to records inside Scarborough's six City wards, even if a selected neighbourhood extends beyond them.",
  "composition-embed-omitted": "{{SHOWN}} dated updates shown from {{ELIGIBLE}} eligible records. {{OMITTED}} left out to fit the chosen space. Here's the boundary wrinkle: DineSafe coverage is limited to records inside Scarborough's six City wards, even if a selected neighbourhood extends beyond them.",
  "finding-legacy": "This saved preview may omit findings. Open the City report for the full inspection.",
  "finding-untranslated": "The City recorded an additional finding. Its original wording is in the source details below; check the official report for its meaning.",
  "finding-empty": "No finding text is supplied here. This is not a claim that the inspection found no problems.",
  "finding-source-title": "Original findings and source details",
  "finding-outcome": "City outcome: {{STATUS}}. Inspection date: {{DATE}}.",
  "finding-category": "City category: {{CATEGORY}}",
  "finding-coverage-one": "1 available finding in the City's records for this date and outcome. The source does not supply an inspection identifier; check the official report for the full inspection.",
  "finding-coverage-many": "{{COUNT}} available findings in the City's records for this date and outcome. The source does not supply an inspection identifier; check the official report for the full inspection."
});

const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
const required = (value, field) => {
  if (typeof value !== 'string' || !value.trim()) throw new TypeError('Missing verified voice fact: ' + field);
  return value;
};

/** The caller escapes interpolated text for HTML; use textContent for DOM. */
export function renderStaticCopy(key, fields = {}, read = currentCopy) {
  if (!own(SCARB_COPY, key)) throw new TypeError('Unregistered Scarb copy: ' + key);
  const template=read('static.'+key,SCARB_COPY[key]);
  const sourceFields=[...SCARB_COPY[key].matchAll(/\{\{([A-Z][A-Z0-9]*)\}\}/g)].map(match=>match[1]).sort();
  const acceptedFields=[...template.matchAll(/\{\{([A-Z][A-Z0-9]*)\}\}/g)].map(match=>match[1]).sort();
  if(JSON.stringify(sourceFields)!==JSON.stringify(acceptedFields))throw new TypeError('Accepted copy changed factual placeholders');
  const names=new Set([...template.matchAll(/\{\{([A-Z][A-Z0-9]*)\}\}/g)].map(match=>match[1]));
  if(!fields || typeof fields!=='object' || Array.isArray(fields) || Object.keys(fields).some(name=>!names.has(name)))throw new TypeError('Unexpected copy field');
  if(names.has('COUNT') && (!Number.isSafeInteger(fields.COUNT) || fields.COUNT<0))throw new TypeError('Invalid copy count');
  if(names.has('NAME') && (typeof fields.NAME!=='string' || !fields.NAME.trim()))throw new TypeError('Invalid copy name');
  return template.replace(/\{\{([A-Z][A-Z0-9]*)\}\}/g, (_, name) => {
    if (!own(fields, name) || !['string', 'number'].includes(typeof fields[name]) || (typeof fields[name]==='number' && !Number.isFinite(fields[name]))) {
      throw new TypeError('Missing copy field: ' + name);
    }
    return String(fields[name]);
  });
}

export function staticCopy(key,fields={}) {return renderStaticCopy(key,fields);}

/** Source-backed narrative only. No invention of discoveries or openings. */
function communityDraft(kind, facts = {}) {
  switch (kind) {
    case 'heading':
      return "Here's what turned up in the DineSafe records for " + required(facts.name, 'name');
    case 'period':
      return "Here's the time window I checked: information added " +
        (facts.inclusive ? 'from ' : 'after ') + required(facts.start, 'start') +
        ' through ' + required(facts.end, 'end') +
        '. The inspections themselves may have happened earlier; I show each inspection date separately.';
    case 'event': {
      const name = required(facts.name, 'name');
      const status = required(facts.status, 'status');
      const inspected = required(facts.inspected, 'inspection date');
      const recorded = required(facts.recorded, 'first-recorded date');
      const prefix = facts.nearby ? 'From nearby: ' : '';
      let observation;
      if (facts.eventKind === 'first_seen') {
        observation = name + ' appeared in the records I checked for the first time (not a confirmed opening).';
      } else if (facts.eventKind === 'status_changed' && facts.previousStatus) {
        observation = 'A change worth checking in the original record: ' + name +
          ' moved from a recorded ' + required(facts.previousStatus, 'previous status') +
          ' to ' + status + '.';
      } else {
        observation = 'Another dated inspection update turned up for ' + name + '.';
      }
      return prefix + observation + ' DineSafe recorded ' + status + ' for the inspection on ' +
        inspected + '. Scarb.TO first recorded this information on ' + recorded + '.';
    }
    case 'boundary-note': {
      const note = required(facts.note, 'boundary note');
      const standard = 'Only records inside the qualified six Scarborough wards are included. City neighbourhoods can cross those wards; this is not necessarily a whole-neighbourhood total.';
      if (note === standard) {
        return "Here's an interesting boundary wrinkle: some neighbourhoods cross Scarborough's six City ward lines. I count only DineSafe records inside those wards, so this may be a slice of a neighbourhood, not its whole total.";
      }
      return 'A boundary detail worth keeping in view: ' + note;
    }
    case 'footer':
      required(facts.releaseId, 'evidence release');
      return `Edition revision 1. Information cut-off: ${required(facts.cutoff, 'information cut-off')}.\nCity of Toronto DineSafe: https://open.toronto.ca/dataset/dinesafe/\nOpen Government Licence - Toronto: https://open.toronto.ca/open-data-licence/\nInformation checked ${required(facts.checked, 'checked date')}. Evidence: https://scarb.to/community/evidence/?release=${facts.releaseId}\nPrepared with Scarb.TO. Keep the downloaded receipt with this edition. Scarb.TO's editorial voice is AI-assisted, not first-hand reporting.`;
    case 'limitations':
      return "One detail I never want to skip: these dated inspection results are not restaurant ratings or a guarantee of conditions today. Check the official DineSafe record for anything newer.";
    case 'stale':
      return "I couldn't check for anything newer than " + required(facts.checked, 'last checked') +
        '. This edition does not cover later information.';
    case 'changed':
      return "The selected areas or settings changed since the previous edition. That makes this a different view of the records, not a like-for-like comparison.";
    case 'snapshot':
      if (!Number.isSafeInteger(facts.count) || facts.count < 0) throw new TypeError('Invalid record count');
      return "Here's a useful bit of context: this selection contains " + facts.count +
        ' DineSafe establishment source records from the snapshot checked ' +
        required(facts.checked, 'last checked') +
        ". That's not the number of changes during this period, or necessarily the number of distinct businesses.";
    case 'empty':
      return "Well, this is interesting in its own quiet way: I found no new updates in the DineSafe records checked for these areas and dates. That doesn't mean nothing happened. The source dates above show exactly what I checked.";
    case 'embed-summary': {
      const {shown, eligible, omitted} = facts;
      if (![shown, eligible, omitted].every(n => Number.isSafeInteger(n) && n >= 0) || shown > eligible) {
        throw new TypeError('Invalid validated update counts');
      }
      return shown + ' dated updates shown from ' + eligible + ' eligible records.' +
        (omitted ? ' ' + omitted + ' left out to fit the chosen space.' : '') +
        " Here's the boundary wrinkle: DineSafe coverage is limited to records inside Scarborough's six City wards, even if a selected neighbourhood extends beyond them.";
    }
    default:
      throw new TypeError('Unregistered Scarb composition: ' + kind);
  }
}

// Exact reviewed safety translations, never rewritten from arbitrary source wording.
const translations=new Map([
  ...SOURCE_TRANSLATIONS,
  ['food premise maintained in manner permitting adverse effect on food - sec. 7(1)(a)(iii)','Conditions at the premises could adversely affect the food. This finding does not establish that contamination or illness occurred.'],
  ['fail to maintain handwashing stations (liquid soap and paper towels) - sec. 7(3)(c)','Handwashing stations were not properly maintained with liquid soap and paper towels.'],
  ['fail to protect food from contamination or adulteration - sec. 26(1)','Food was not adequately protected from contamination or adulteration. This does not establish that contamination occurred.'],
  ['maintain potentially hazardous foods at internal temperature between 4°c and 60°c - sec. 27(1)','Food requiring temperature control was held at an internal temperature between 4°C and 60°C.'],
  ['fail to ensure equipment surface cleaned as necessary - sec. 22','Equipment surfaces were not cleaned as required.'],
]);

function findingDraft(kind, facts={}) {
  switch(kind) {
    case 'translation': return typeof facts.wording==='string' ? translations.get(facts.wording.toLocaleLowerCase('en-CA')) || null : null;
    case 'coverage':
      if (!Number.isSafeInteger(facts.count) || facts.count < 0) throw new TypeError('Invalid finding count');
      return `${facts.count} available finding${facts.count===1?'':'s'} in the City's records for this date and outcome. The source does not supply an inspection identifier; check the official report for the full inspection.`;
    case 'legacy': return 'This saved preview may omit findings. Open the City report for the full inspection.';
    case 'untranslated': return 'The City recorded an additional finding. Its original wording is in the source details below; check the official report for its meaning.';
    case 'empty': return 'No finding text is supplied here. This is not a claim that the inspection found no problems.';
    case 'source-title': return 'Original findings and source details';
    case 'outcome': return `City outcome: ${required(facts.status,'outcome')}. Inspection date: ${required(facts.date,'inspection date')}.`;
    case 'category': return `City category: ${required(facts.category,'category')}`;
    default: throw new TypeError('Unregistered finding composition: '+kind);
  }
}


// Accepted templates are separate from immutable source drafts. Runtime private
// publisher values are substituted locally and are never authoring/API inputs.
export function communityVoice(kind,facts={}) {
  communityDraft(kind,facts); // Preserve the existing factual/type contracts.
  let key='composition-'+kind,fields={};
  if(kind==='heading')fields={NAME:facts.name};
  else if(kind==='period'){key+='-'+(facts.inclusive?'inclusive':'exclusive');fields={START:facts.start,END:facts.end};}
  else if(kind==='event'){
    const variant=facts.eventKind==='first_seen'?'first_seen':facts.eventKind==='status_changed'&&facts.previousStatus?'status_changed':'new_inspection';
    key+='-'+variant+(facts.nearby?'-nearby':'');fields={NAME:facts.name,STATUS:facts.status,INSPECTED:facts.inspected,RECORDED:facts.recorded};
    if(variant==='status_changed')fields.PREVIOUS=facts.previousStatus;
  } else if(kind==='boundary-note'){
    const standard='Only records inside the qualified six Scarborough wards are included. City neighbourhoods can cross those wards; this is not necessarily a whole-neighbourhood total.';
    key=facts.note===standard?'composition-boundary-standard':'composition-boundary-other';if(facts.note!==standard)fields={NOTE:facts.note};
  } else if(kind==='footer')fields={CUTOFF:facts.cutoff,CHECKED:facts.checked,RELEASEID:facts.releaseId};
  else if(kind==='stale')fields={CHECKED:facts.checked};
  else if(kind==='snapshot')fields={COUNT:facts.count,CHECKED:facts.checked};
  else if(kind==='embed-summary'){key='composition-embed-'+(facts.omitted?'omitted':'all');fields={SHOWN:facts.shown,ELIGIBLE:facts.eligible};if(facts.omitted)fields.OMITTED=facts.omitted;}
  return staticCopy(key,fields);
}
const findingAcceptedKeys=new Map([["fail to clean utensils as often as necessary - sec. 21(2)", "finding-explanation-fb4d5d15fe5e5507"], ["fail to collect waste when necessary to maintain sanitary condition - sec. 12", "finding-explanation-166112e70da21005"], ["fail to ensure completion of food handling training by food handler or supervisor - sec. 32", "finding-explanation-7155e6e6c00df05f"], ["fail to ensure equipment surface cleaned as necessary - sec. 22", "finding-explanation-0baa6b9f81867a50"], ["fail to ensure equipment surface sanitized as necessary - sec. 22", "finding-explanation-d1a54a8320e2699e"], ["fail to ensure facility surface cleaned as necessary - sec. 22", "finding-explanation-990b53cbf14a721e"], ["fail to ensure facility surface sanitized as necessary - sec. 22", "finding-explanation-250836a55400e2d2"], ["fail to ensure food handler in food premise practices good personal hygiene - sec. 33(1)(b)", "finding-explanation-0cccdf046fd4e2e1"], ["fail to ensure food handler in food premise protects against contamination by hair - sec.  33(1)(d)", "finding-explanation-1af905522aa2a33f"], ["fail to ensure food handler in food premise wears clean outer garments - sec. 33(1)(c)", "finding-explanation-102fa7236342db38"], ["fail to ensure presence of food handler or supervisor during all hours of operation - sec. 32", "finding-explanation-9ee635f015842859"], ["fail to maintain handwashing stations (liquid soap and paper towels) - sec. 7(3)(c)", "finding-explanation-f882cb7b45e3af65"], ["fail to maintain ventilation system to ensure elimination of smoke - sec. 11", "finding-explanation-be850ff3201189da"], ["fail to post inspection results in accordance with inspector's request - sec. 6", "finding-explanation-e4aa7550e59bc4b0"], ["fail to produce most recent food safety inspection report(s) - sec. 545-157(e)(5)", "finding-explanation-0ac7faf6108da739"], ["fail to protect against breeding of pests - sec. 13(1)", "finding-explanation-a453f43f952c3107"], ["fail to protect against entry of pests - sec. 13(1)", "finding-explanation-b5624e0779fc3f7c"], ["fail to protect against harbouring of pests - sec. 13(1)", "finding-explanation-7ea38bf0b6710acb"], ["fail to protect food from contamination or adulteration - sec. 26(1)", "finding-explanation-376035dc95fc05a1"], ["fail to provide adequate number of handwashing stations - sec. 7(3)(c)", "finding-explanation-55b1373fe438a221"], ["fail to provide required illumination during all hours of operation - sec. 10", "finding-explanation-2fc75dccd864addb"], ["fail to provide thermometer in hot-holding equipment - sec. 30(b)", "finding-explanation-8c997947787a0cee"], ["fail to provide thermometer in refrigeration equipment - sec. 30(b)", "finding-explanation-71163b5e8ba09bb7"], ["fail to remove garbage when necessary to maintain sanitary condition - sec. 12", "finding-explanation-f47febd1613c1fbb"], ["fail to remove wastes when necessary to maintain sanitary condition - sec. 12", "finding-explanation-6d4e8868216f592c"], ["food premise maintained in manner permitting adverse effect on food - sec. 7(1)(a)(iii)", "finding-explanation-549749191cc32f62"], ["food premise maintained in manner to permit contamination of single-service containers - sec. 7(1)(h)", "finding-explanation-49cb0402e13be124"], ["food premise not maintained to keep food-handling room free from equipment not regularly used - sec. 7(1)(f)", "finding-explanation-e9be03fc092ac361"], ["food premise not maintained to keep food-handling room free from materials not regularly used - sec. 7(1)(f)", "finding-explanation-aa1edc84017fdbca"], ["food premise not maintained to permit cleaning of ceilings - sec. 7(1)(d)", "finding-explanation-97881a45d10a023d"], ["food premise not maintained to permit cleaning of walls  - sec. 7(1)(d)", "finding-explanation-e929a3db8cf382f3"], ["food premise not maintained to permit sanitary maintenance of ceilings - sec. 7(1)(d)", "finding-explanation-c99c97cd13926bfb"], ["food premise not maintained to permit sanitary maintenance of walls - sec. 7(1)(d)", "finding-explanation-664e0ed0696a1822"], ["food premise not maintained with ceilings in good repair in food-handling room - sec. 7(1)(g)", "finding-explanation-3fa8b60a24dfb615"], ["food premise not maintained with clean ceiling in food-handling room - sec. 7(1)(g)", "finding-explanation-60f58672d67dea9b"], ["food premise not maintained with clean floors in food-handling room - sec. 7(1)(g)", "finding-explanation-9ffe7b3753d0a052"], ["food premise not maintained with clean walls in food-handling room - sec. 7(1)(g)", "finding-explanation-e6a840398ac06901"], ["food premise not maintained with floors in good repair in food-handling room - sec. 7(1)(g)", "finding-explanation-233b3a3934b6fc0d"], ["food premise not maintained with food handling room in sanitary condition - sec. 7(1)(e)", "finding-explanation-f9eb75190a51c30d"], ["food premise not maintained with non-absorbent floor surface where food handled - sec. 7(1)(c)(i)", "finding-explanation-890e0fb1977b8965"], ["food premise not maintained with smooth floor surface where food handled - sec. 7(1)(c)(i)", "finding-explanation-544b08c684a7ba77"], ["food premise not maintained with smooth floor surface where utensils cleaned - sec. 7(1)(c)(ii)", "finding-explanation-4ff4bb2e488f0940"], ["food premise not maintained with tight floor surface where food handled - sec. 7(1)(c)(i)", "finding-explanation-43d5b22e576e6a48"], ["food premise not maintained with tight floor surface where utensils cleaned - sec. 7(1)(c)(ii)", "finding-explanation-48e8c6a0de01d3df"], ["food premise not maintained with walls in good repair in food-handling room - sec. 7(1)(g)", "finding-explanation-0bd1898c410b80ab"], ["handwashing stations not conveniently accessible by food handlers - sec. 7(3)(c)", "finding-explanation-9f0584588789d2f6"], ["no license available at time of inspection. a referral has been made to municipal licensing and standards.", "finding-explanation-3c52d9cf17d280b1"], ["operate food premise - appliances not constructed to permit cleaning - sec. 9", "finding-explanation-3be26fcb2bea0ad3"], ["operate food premise - appliances not constructed to permit maintenance in sanitary condition - sec. 9", "finding-explanation-c17bbbf70409c000"], ["operate food premise - equipment not arranged to permit cleaning - sec. 9", "finding-explanation-e30d88d467d25736"], ["operate food premise - equipment not arranged to permit maintenance in sanitary condition - sec. 9", "finding-explanation-956d3f8b5784c964"], ["operate food premise - equipment not constructed to permit cleaning - sec. 9", "finding-explanation-d06c0b1ad56687b4"], ["operate food premise - equipment not constructed to permit maintenance in sanitary condition - sec. 9", "finding-explanation-88eeb889ed6c8232"], ["operate food premise - fail to equip sanitary facility with single service towels or dryer - sec. 25(3)(e)", "finding-explanation-40a5c4ce267befac"], ["operate food premise - fail to equip sanitary facility with soap or detergent - sec. 24(3)(d)", "finding-explanation-c81e84fecdde1720"], ["operate food premise - fail to equip sanitary facility with toilet paper - sec. 25(3)(b)", "finding-explanation-2a5a4167ff430b78"], ["operate food premise - fail to keep sanitary facility in good repair - sec. 25(2)", "finding-explanation-f9ae482f2342e759"], ["operate food premise - fail to keep sanitary facility sanitary - sec. 25(2)", "finding-explanation-301b33152fa2ae4e"], ["operate food premise - furniture not arranged to permit maintenance in sanitary condition - sec. 9", "finding-explanation-982425a3e677e82b"], ["operate food premise - furniture not constructed to permit cleaning - sec. 9", "finding-explanation-f1c3821f2efad5f0"], ["operate food premise - furniture not constructed to permit maintenance in sanitary condition - sec. 9", "finding-explanation-81cb5ba276533b89"], ["operate food premise - mechanical equipment not maintained to maintain rinse water at 82 c - sec. 20(1)(a)(ii)(a)", "finding-explanation-a1d039c638d480c8"], ["operate food premise - mechanical equipment not maintained to maintain rinse water at 82°c - sec. 20(1)(a)(ii)(a)", "finding-explanation-311c575d18c08f88"], ["operate food premise - mechanical equipment not maintained to provide clean wash water - sec. 20(1)(a)(i)", "finding-explanation-2fa203d49f248dbf"], ["operate food premise - mechanical equipment not maintained to provide sufficient chemical solution rinse - sec. 20(1)(a)(ii)(b)", "finding-explanation-99e18a7c0db2be70"], ["operate food premise -rinse water temperature thermometer not easily readable  - sec.  20(1)(b)", "finding-explanation-1eaa43e01db597ad"], ["operate mobile food premise -- no gauge on waste tank - sec. 4(1)(d)", "finding-explanation-bc87fa104f07ca31"], ["sanitize utensils in chlorine solution of less than 100 p.p.m. of available chlorine - sec. 19(b)", "finding-explanation-4687388b4399098f"], ["sanitize utensils in quaternary ammonium compound solution of less than 200 p.p.m. - sec. 19(c)", "finding-explanation-0d7b4ce606acee55"], ["sanitize utensils using agent for which test reagent not readily available - sec. 19(e)(iii)", "finding-explanation-453b1dae8806a855"], ["thermometer in hot-holding equipment not easily readable - sec. 30(b)", "finding-explanation-3b80f2b85f700014"], ["thermometer in refrigeration equipment not easily readable - sec. 30(b)", "finding-explanation-c484c25ea66993ed"], ["use equipment not suitable for intended purpose - sec. 8(1)(d)", "finding-explanation-a0d4bd970117a106"], ["use food equipment not of readily cleanable form - sec.  8(1)(c)", "finding-explanation-7507fe18e4efce30"], ["use food equipment not of readily cleanable material - sec.  8(1)(c)", "finding-explanation-54a68a5e7db206d7"], ["use food equipment not of sound and tight construction - sec. 8(1)(a)", "finding-explanation-fcf37504d73b4996"], ["use multi-service articles not of readily cleanable form - sec. 8(1)(c)", "finding-explanation-2c28027af8513b95"], ["use multi-service articles not suitable for intended purpose - sec. 8(1)(d)", "finding-explanation-e515079639b0b2ad"], ["use non-corrosion resistant equipment in contact with food - sec.  8(2)(a)", "finding-explanation-c4fbfa3a08039d7c"], ["use non-corrosion resistant utensils in contact with food - sec. 8(2)(a)", "finding-explanation-ff5650b4f3e1d752"], ["use shelves not of readily cleanable design - sec. 31", "finding-explanation-55eb3a9acbeba3d6"], ["use towel used for other purpose for cleaning food contact surface - sec. 16(c)", "finding-explanation-4586d24a972736ff"], ["use utensils not free from cracks in contact with food - sec. 8(2)(b)", "finding-explanation-2f130e4ac268594b"], ["use utensils not in good repair - sec. 8(1)(b)", "finding-explanation-09a869a514276b26"], ["use utensils not non-toxic in contact with food - sec. 8(2)(a)", "finding-explanation-20363154ac4a238b"], ["use utensils not of readily cleanable form - sec.  8(1)(c)", "finding-explanation-496fe84fd1aa10a6"], ["use utensils not of readily cleanable material - sec.  8(1)(c)", "finding-explanation-dc61761581abe33d"], ["use utensils not of sound and tight construction - sec. 8(1)(a)", "finding-explanation-ffc9683a1081a818"], ["use utensils not suitable for intended purpose - sec. 8(1)(d)", "finding-explanation-5072e77f0a9cf64c"], ["maintain potentially hazardous foods at internal temperature between 4°c and 60°c - sec. 27(1)", "finding-explanation-7e0c1202c0f59cfd"]]);
export function findingVoice(kind,facts={}) {
  const validated=findingDraft(kind,facts);
  if(kind==='translation'){if(validated===null)return null;return staticCopy(findingAcceptedKeys.get(facts.wording.toLocaleLowerCase('en-CA')));}
  if(kind==='coverage')return facts.count===1?staticCopy('finding-coverage-one'):staticCopy('finding-coverage-many',{COUNT:facts.count});
  if(kind==='outcome')return staticCopy('finding-outcome',{STATUS:facts.status,DATE:facts.date});
  if(kind==='category')return staticCopy('finding-category',{CATEGORY:facts.category});
  return staticCopy('finding-'+kind);
}
