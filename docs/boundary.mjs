/** Official Scarborough Community Council display boundary helpers (EPSG:4326). */
export const COUNCIL_BOUNDARY_ID = 2476922;
export const COUNCIL_BOUNDARY_NAME = 'Scarborough Community Council';
export const COUNCIL_BOUNDARY_BOUNDS = [[-79.3413178929128, 43.6716713902779], [-79.115243188678, 43.8554571861712]];

function coordinatesOf(geometry) {
  if (geometry?.type === 'Polygon') return geometry.coordinates;
  if (geometry?.type === 'MultiPolygon') return geometry.coordinates.flat();
  throw new TypeError('Council boundary must be Polygon or MultiPolygon');
}

function signedArea(ring) {
  let area = 0;
  for (let i = 1; i < ring.length; i++) area += ring[i - 1][0] * ring[i][1] - ring[i][0] * ring[i - 1][1];
  return area / 2;
}

export function validateCouncilBoundary(feature) {
  if (feature?.type !== 'Feature' || feature.properties?.AREA_ID !== COUNCIL_BOUNDARY_ID || feature.properties?.AREA_NAME !== COUNCIL_BOUNDARY_NAME) {
    throw new TypeError('Unexpected Scarborough Community Council feature identity');
  }
  const polygons = feature.geometry?.type === 'Polygon' ? [feature.geometry.coordinates] : null;
  if (!polygons?.length || polygons[0].length !== 1) throw new TypeError('Qualified council boundary must remain one polygon exterior without holes');
  let count = 0;
  let west = Infinity, south = Infinity, east = -Infinity, north = -Infinity;
  for (const polygon of polygons) {
    if (!Array.isArray(polygon) || !polygon.length) throw new TypeError('Council polygon has no rings');
    for (const ring of polygon) {
      if (!Array.isArray(ring) || ring.length < 4 || ring[0][0] !== ring.at(-1)[0] || ring[0][1] !== ring.at(-1)[1]) throw new TypeError('Council rings must be closed');
      for (const point of ring) {
        if (!Array.isArray(point) || point.length < 2 || !Number.isFinite(point[0]) || !Number.isFinite(point[1]) || point[0] < -180 || point[0] > 180 || point[1] < -90 || point[1] > 90) throw new TypeError('Council geometry must use finite EPSG:4326 coordinates');
        west = Math.min(west, point[0]); east = Math.max(east, point[0]); south = Math.min(south, point[1]); north = Math.max(north, point[1]); count++;
      }
    }
  }
  const expected = COUNCIL_BOUNDARY_BOUNDS;
  if (count < 100 || Math.abs(west - expected[0][0]) > 1e-8 || Math.abs(south - expected[0][1]) > 1e-8 || Math.abs(east - expected[1][0]) > 1e-8 || Math.abs(north - expected[1][1]) > 1e-8) throw new TypeError('Council boundary extent does not match the qualified source');
  return feature;
}

/** A world polygon with the authoritative boundary as its hole; no feature is filtered. */
export function outsideMask(feature) {
  validateCouncilBoundary(feature);
  const polygons = feature.geometry.type === 'Polygon' ? [feature.geometry.coordinates] : feature.geometry.coordinates;
  const exterior = [[[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]]];
  const holes = polygons.flatMap(polygon => polygon.map(ring => signedArea(ring) > 0 ? [...ring].reverse() : ring));
  return { type: 'FeatureCollection', features: [{ type: 'Feature', properties: { role: 'outside-scarborough-mask' }, geometry: { type: 'Polygon', coordinates: [...exterior, ...holes] } }] };
}

export function cameraBoundsForViewport(width, height, buffer = .08) {
  if (![width, height].every(Number.isFinite) || width <= 32 || height <= 32 || buffer < 0 || buffer > .5) throw new TypeError('Invalid viewport for boundary camera');
  const [[west, south], [east, north]] = COUNCIL_BOUNDARY_BOUNDS;
  const mercatorY=latitude=>Math.log(Math.tan(Math.PI/4+latitude*Math.PI/360));
  const inverseMercatorY=value=>(2*Math.atan(Math.exp(value))-Math.PI/2)*180/Math.PI;
  const midLat = (south + north) / 2;
  const centerX=(west+east)/2*Math.PI/180,centerY=(mercatorY(south)+mercatorY(north))/2;
  let dx=(east-west)*Math.PI/180*(1+2*buffer),dy=(mercatorY(north)-mercatorY(south))*(1+2*buffer);
  const aspect = (width - 32) / (height - 32);
  if (dx / dy < aspect) dx = dy * aspect; else dy = dx / aspect;
  return [[(centerX-dx/2)*180/Math.PI,inverseMercatorY(centerY-dy/2)],[(centerX+dx/2)*180/Math.PI,inverseMercatorY(centerY+dy/2)]];
}
