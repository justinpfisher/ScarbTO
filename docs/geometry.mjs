/** Geometry helpers for the existing City neighbourhood polygons. */
function coordinateKey(point) {
  if (!Array.isArray(point) || point.length < 2 || !Number.isFinite(point[0]) || !Number.isFinite(point[1])) throw new TypeError('Expected finite longitude/latitude coordinates');
  return `${point[0]},${point[1]}`;
}
function polygonRings(geometry) {
  if (!geometry || !Array.isArray(geometry.coordinates)) throw new TypeError('Expected Polygon or MultiPolygon geometry');
  if (geometry.type === 'Polygon') return geometry.coordinates;
  if (geometry.type === 'MultiPolygon') return geometry.coordinates.flatMap(polygon => polygon);
  throw new TypeError('Expected Polygon or MultiPolygon geometry');
}

/** Dissolve exact shared neighborhood edges into a closed outer/inner boundary. */
export function unionBoundary(features) {
  if (!Array.isArray(features) || features.length === 0) throw new TypeError('At least one polygon feature is required');
  const segments = new Map();
  for (const feature of features) for (const ring of polygonRings(feature?.geometry)) {
    if (!Array.isArray(ring) || ring.length < 4 || coordinateKey(ring[0]) !== coordinateKey(ring.at(-1))) throw new TypeError('Polygon rings must be closed and contain at least four positions');
    for (let i=1;i<ring.length;i++) {
      const a=coordinateKey(ring[i-1]),b=coordinateKey(ring[i]);
      if(a===b)continue;
      const key=a<b?`${a}|${b}`:`${b}|${a}`;
      const edge=segments.get(key)||{a:a<b?a:b,b:a<b?b:a,count:0};
      if(++edge.count>2)throw new TypeError('Overlapping polygon boundaries are ambiguous');
      segments.set(key,edge);
    }
  }
  const boundary=[...segments.values()].filter(edge=>edge.count===1);
  if(!boundary.length)throw new TypeError('Polygon union has no boundary');
  const adjacency=new Map();
  boundary.forEach((edge,index)=>{
    for(const [point,other] of [[edge.a,edge.b],[edge.b,edge.a]]){
      const values=adjacency.get(point)||[];values.push({index,other});adjacency.set(point,values);
    }
  });
  for(const [point,edges] of adjacency)if(edges.length!==2)throw new TypeError(`Boundary is not closed at ${point}`);
  const unused=new Set(boundary.map((_,index)=>index)),rings=[];
  while(unused.size){
    const firstIndex=unused.values().next().value,start=boundary[firstIndex].a;
    let current=start,previous=-1;const ring=[start];
    while(true){
      const next=adjacency.get(current).find(edge=>edge.index!==previous&&unused.has(edge.index));
      if(!next)throw new TypeError('Boundary traversal did not close');
      unused.delete(next.index);current=next.other;ring.push(current);
      if(current===start)break;
      previous=next.index;
      if(ring.length>boundary.length+1)throw new TypeError('Boundary traversal exceeded edge count');
    }
    if(ring.length<4)throw new TypeError('Boundary ring is too short');
    rings.push(ring.map(point=>point.split(',').map(Number)));
  }
  return {type:'FeatureCollection',features:[{type:'Feature',properties:{role:'scarborough-outline'},geometry:{type:'MultiLineString',coordinates:rings}}]};
}

export function boundsFromFeatures(features) {
  if(!Array.isArray(features)||!features.length)return null;
  let west=Infinity,south=Infinity,east=-Infinity,north=-Infinity,count=0;
  const visit=value=>{
    if(!Array.isArray(value))throw new TypeError('Invalid polygon coordinates');
    if(typeof value[0]==='number'){
      if(!Number.isFinite(value[0])||!Number.isFinite(value[1]))throw new TypeError('Non-finite map coordinate');
      west=Math.min(west,value[0]);east=Math.max(east,value[0]);south=Math.min(south,value[1]);north=Math.max(north,value[1]);count++;return;
    }
    for(const child of value)visit(child);
  };
  for(const feature of features)visit(polygonRings(feature?.geometry));
  return count?[[west,south],[east,north]]:null;
}

export function expandBounds(bounds,{longitude=0,latitude=0}={}) {
  if(!Array.isArray(bounds)||bounds.length!==2||!bounds.flat().every(Number.isFinite)||longitude<0||latitude<0)throw new TypeError('Expected valid bounds and non-negative padding');
  return [[bounds[0][0]-longitude,bounds[0][1]-latitude],[bounds[1][0]+longitude,bounds[1][1]+latitude]];
}

export function responsiveMapPadding(width,height) {
  if(!(Number.isFinite(width)&&Number.isFinite(height)&&width>0&&height>0))throw new TypeError('Map size must be positive');
  const shortSide=Math.min(width,height);
  const vertical=Math.max(12,Math.min(30,Math.round(shortSide*.035)));
  const horizontal=Math.max(12,Math.min(30,Math.round(width*.025)));
  return {top:vertical,bottom:vertical,left:horizontal,right:horizontal};
}

const SCARBOROUGH_WARD_CODES=['20','21','22','23','24','25'];
const MAX_WARD_RESPONSE_BYTES=20*1024*1024;
const MAX_WARD_VERTICES=250000;
const MAX_MERCATOR_LATITUDE=85.05112878;

/** Build the exact bounded public GIS query; this function performs no network request. */
export function scarboroughWardQueryURL(){
  const url=new URL('https://gis.toronto.ca/arcgis/rest/services/cot_geospatial22/FeatureServer/0/query');
  url.searchParams.set('where',"AREA_SHORT_CODE IN ('20','21','22','23','24','25')");
  url.searchParams.set('outFields','AREA_ID,AREA_SHORT_CODE,AREA_LONG_CODE,AREA_NAME,OBJECTID');
  url.searchParams.set('returnGeometry','true');
  url.searchParams.set('outSR','4326');
  url.searchParams.set('f','geojson');
  url.searchParams.set('orderByFields','AREA_SHORT_CODE');
  url.searchParams.set('resultRecordCount','7');
  return url.toString();
}

/** Validate a downloaded full administrative ward collection before using it. */
export function validateScarboroughWardFeatures(features,{responseBytes,maxBytes=MAX_WARD_RESPONSE_BYTES,maxVertices=MAX_WARD_VERTICES}={}){
  if(!Number.isSafeInteger(responseBytes)||responseBytes<1||responseBytes>maxBytes)throw new TypeError('Ward response is missing or exceeds the byte limit');
  if(!Array.isArray(features)||features.length!==SCARBOROUGH_WARD_CODES.length)throw new TypeError('Expected exactly six Scarborough ward features');
  const seen=new Set();let vertices=0;
  const checked=features.map(feature=>{
    const code=String(feature?.properties?.AREA_SHORT_CODE??'');
    if(!SCARBOROUGH_WARD_CODES.includes(code)||seen.has(code))throw new TypeError('Ward codes must be unique and exactly 20 through 25');
    seen.add(code);
    for(const value of ['AREA_ID','AREA_LONG_CODE','AREA_NAME','OBJECTID'])if(feature?.properties?.[value]===undefined||feature?.properties?.[value]===null)throw new TypeError(`Ward feature is missing ${value}`);
    const rings=polygonRings(feature?.geometry);
    if(!rings.length)throw new TypeError('Ward geometry must contain polygon rings');
    for(const ring of rings){
      if(!Array.isArray(ring)||ring.length<4||coordinateKey(ring[0])!==coordinateKey(ring.at(-1)))throw new TypeError('Ward rings must be closed and contain at least four positions');
      vertices+=ring.length;
      for(const position of ring){
        if(!Array.isArray(position)||position.length<2||!Number.isFinite(position[0])||!Number.isFinite(position[1])||position[0]<-180||position[0]>180||position[1]<-90||position[1]>90)throw new TypeError('Ward geometry must use finite geographic coordinates');
      }
    }
    return feature;
  });
  if(SCARBOROUGH_WARD_CODES.some(code=>!seen.has(code)))throw new TypeError('Ward collection is missing an expected Scarborough code');
  if(vertices>maxVertices)throw new TypeError('Ward geometry exceeds the vertex limit');
  return checked.sort((a,b)=>String(a.properties.AREA_SHORT_CODE).localeCompare(String(b.properties.AREA_SHORT_CODE)));
}

function mercatorY(latitude){
  const radians=Math.max(-MAX_MERCATOR_LATITUDE,Math.min(MAX_MERCATOR_LATITUDE,latitude))*Math.PI/180;
  return Math.log(Math.tan(Math.PI/4+radians/2));
}
function inverseMercatorY(value){return (2*Math.atan(Math.exp(value))-Math.PI/2)*180/Math.PI;}

/** Expand projected bounds to the usable viewport aspect so maxBounds cannot force edge clipping. */
export function aspectAwareMapBounds(bounds,width,height,{padding=16,bufferFraction=.08}={}){
  if(!Array.isArray(bounds)||bounds.length!==2||!bounds.flat().every(Number.isFinite)||!(width>2*padding&&height>2*padding)||!(bufferFraction>=0&&bufferFraction<=.5))throw new TypeError('Expected valid bounds and viewport dimensions');
  const [[west,south],[east,north]]=bounds;
  if(west>=east||south>=north||west< -180||east>180||south< -90||north>90)throw new TypeError('Map bounds are invalid');
  const x1=west*Math.PI/180,x2=east*Math.PI/180,y1=mercatorY(south),y2=mercatorY(north);
  const centerX=(x1+x2)/2,centerY=(y1+y2)/2;
  let projectedWidth=(x2-x1)*(1+2*bufferFraction),projectedHeight=(y2-y1)*(1+2*bufferFraction);
  const viewportAspect=(width-2*padding)/(height-2*padding);
  if(projectedWidth/projectedHeight<viewportAspect)projectedWidth=projectedHeight*viewportAspect;
  else projectedHeight=projectedWidth/viewportAspect;
  return [
    [(centerX-projectedWidth/2)*180/Math.PI,inverseMercatorY(centerY-projectedHeight/2)],
    [(centerX+projectedWidth/2)*180/Math.PI,inverseMercatorY(centerY+projectedHeight/2)],
  ];
}

