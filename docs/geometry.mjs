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
