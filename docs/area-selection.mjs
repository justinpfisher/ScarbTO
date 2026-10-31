/** Source-linked area identities. Neighbourhood codes and ward intersections are copied
 * from the hash-pinned 2026-10-27 City EPSG:2952 research contract.
 * This map is not a claim that neighbourhoods fit wholly within wards.
 * 2026 officeholders: City Council directory and certified Oct 29 election,
 * effective 2026-11-15 for the 2026-2030 term.
 */
export const NEIGHBOURHOODS = Object.freeze({
  "116": {
    "name": "Steeles",
    "wards": [
      "22"
    ]
  },
  "118": {
    "name": "Tam O'Shanter-Sullivan",
    "wards": [
      "22"
    ]
  },
  "119": {
    "name": "Wexford/Maryvale",
    "wards": [
      "21"
    ]
  },
  "120": {
    "name": "Clairlea-Birchmount",
    "wards": [
      "20"
    ]
  },
  "121": {
    "name": "Oakridge",
    "wards": [
      "20"
    ]
  },
  "122": {
    "name": "Birchcliffe-Cliffside",
    "wards": [
      "20"
    ]
  },
  "123": {
    "name": "Cliffcrest",
    "wards": [
      "20"
    ]
  },
  "124": {
    "name": "Kennedy Park",
    "wards": [
      "20"
    ]
  },
  "125": {
    "name": "Ionview",
    "wards": [
      "20",
      "21"
    ]
  },
  "126": {
    "name": "Dorset Park",
    "wards": [
      "21"
    ]
  },
  "128": {
    "name": "Agincourt South-Malvern West",
    "wards": [
      "22",
      "23"
    ]
  },
  "129": {
    "name": "Agincourt North",
    "wards": [
      "23"
    ]
  },
  "130": {
    "name": "Milliken",
    "wards": [
      "22",
      "23"
    ]
  },
  "133": {
    "name": "Centennial Scarborough",
    "wards": [
      "25"
    ]
  },
  "134": {
    "name": "Highland Creek",
    "wards": [
      "25"
    ]
  },
  "135": {
    "name": "Morningside",
    "wards": [
      "24"
    ]
  },
  "136": {
    "name": "West Hill",
    "wards": [
      "24",
      "25"
    ]
  },
  "138": {
    "name": "Eglinton East",
    "wards": [
      "20",
      "21"
    ]
  },
  "139": {
    "name": "Scarborough Village",
    "wards": [
      "20",
      "24"
    ]
  },
  "140": {
    "name": "Guildwood",
    "wards": [
      "24",
      "25"
    ]
  },
  "141": {
    "name": "Golfdale-Cedarbrae-Woburn",
    "wards": [
      "21",
      "24"
    ]
  },
  "142": {
    "name": "Woburn North",
    "wards": [
      "24"
    ]
  },
  "143": {
    "name": "West Rouge",
    "wards": [
      "25"
    ]
  },
  "144": {
    "name": "Morningside Heights",
    "wards": [
      "23",
      "25"
    ]
  },
  "145": {
    "name": "Malvern West",
    "wards": [
      "23",
      "25"
    ]
  },
  "146": {
    "name": "Malvern East",
    "wards": [
      "23",
      "25"
    ]
  },
  "147": {
    "name": "L'Amoreaux West",
    "wards": [
      "22"
    ]
  },
  "148": {
    "name": "East L'Amoreaux",
    "wards": [
      "22"
    ]
  },
  "156": {
    "name": "Bendale-Glen Andrew",
    "wards": [
      "21"
    ]
  },
  "157": {
    "name": "Bendale South",
    "wards": [
      "21"
    ]
  }
});
export const WARDS = Object.freeze({
  "20": {
    "name": "Scarborough Southwest",
    "councillor": "Parthi Kandavel"
  },
  "21": {
    "name": "Scarborough Centre",
    "councillor": "Michael Thompson"
  },
  "22": {
    "name": "Scarborough-Agincourt",
    "councillor": "Nick Mantas"
  },
  "23": {
    "name": "Scarborough North",
    "councillor": "Jamaal Myers",
    "elected": "Shaun Chen"
  },
  "24": {
    "name": "Scarborough-Guildwood",
    "councillor": "Paul Ainslie"
  },
  "25": {
    "name": "Scarborough-Rouge Park",
    "councillor": "Neethan Shan"
  }
});
export const BOUNDARY_SOURCES = Object.freeze({
  neighbourhood: 'https://open.toronto.ca/dataset/neighbourhoods/',
  ward: 'https://open.toronto.ca/dataset/city-wards/'
});

export function areaFor(kind, code) {
  const key = String(code ?? '');
  const source = kind === 'neighbourhood' ? NEIGHBOURHOODS : kind === 'ward' ? WARDS : null;
  return source && Object.hasOwn(source,key) ? {kind, code:key, ...source[key]} : null;
}

export function areaForName(kind, name) {
  if (typeof name !== 'string') return null;
  const dict = kind === 'neighbourhood' ? NEIGHBOURHOODS : kind === 'ward' ? WARDS : {};
  for (const code of Object.keys(dict)) {
    if (dict[code].name === name) return areaFor(kind, code);
  }
  return null;
}

/** An area is a single geographic filter, never two hidden intersecting filters. */
export function areaMatches(record, state) {
  if (state.areaKind && state.areaCode) {
    const area = areaFor(state.areaKind,state.areaCode);
    if (!area) return false;
    return (state.areaKind === 'neighbourhood' ? record.neighbourhood : record.ward) === area.name;
  }
  return !state.neighbourhood || record.neighbourhood === state.neighbourhood;
}

export function councillorFor(code, at = new Date()) {
  const ward = WARDS[String(code)];
  if (!ward) return null;
  const transition = at.valueOf() >= Date.parse('2026-11-15T05:00:00Z');
  const name = String(code) === '23' && transition ? ward.elected : ward.councillor;
  return {name, role:'City councillor', ward:ward.name,
    transition: String(code) === '23' && !transition ? ward.elected : null,
    checked:'2026-10-31',
    url:'https://www.toronto.ca/city-government/council/members-of-council/councillor-ward-' + encodeURIComponent(code) + '/'};
}

/** The City feed is checked before being projected into static overlay geometry. */
export function validateAreaFeatures(kind, data) {
  const dict = kind === 'neighbourhood' ? NEIGHBOURHOODS : kind === 'ward' ? WARDS : null;
  if (!dict || data?.type !== 'FeatureCollection' || !Array.isArray(data.features)) throw new TypeError('Invalid official area collection');
  if (data.features.length !== Object.keys(dict).length) throw new TypeError('Area count differs from qualified source');
  const seen = new Set();
  for (const feature of data.features) {
    const code = feature?.properties?.AREA_SHORT_CODE;
    const area = areaFor(kind,code);
    if (!area || feature.properties.AREA_NAME !== area.name || seen.has(area.code)) throw new TypeError('Unknown, duplicated or changed official area identity');
    seen.add(area.code);
    const geometry = feature.geometry;
    const polygons = geometry?.type === 'Polygon' ? [geometry.coordinates] : geometry?.type === 'MultiPolygon' ? geometry.coordinates : null;
    if (!Array.isArray(polygons) || !polygons.length) throw new TypeError('Invalid official area geometry');
    for (const polygon of polygons) {
      if (!Array.isArray(polygon) || !polygon.length) throw new TypeError('Empty polygon');
      for (const ring of polygon) {
        if (!Array.isArray(ring) || ring.length < 4) throw new TypeError('Invalid area ring');
        const first = ring[0], last = ring[ring.length-1];
        if (first[0] !== last[0] || first[1] !== last[1]) throw new TypeError('Open area ring');
        for (const point of ring) {
          if (!Array.isArray(point) || point.length < 2 || !Number.isFinite(point[0]) || !Number.isFinite(point[1]) ||
            point[0] < -80 || point[0] > -78 || point[1] < 43 || point[1] > 45) throw new TypeError('Area point outside Toronto');
        }
      }
    }
  }
  return data;
}
