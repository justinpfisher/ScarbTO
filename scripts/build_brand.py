"""Build frozen, City-derived Scarb.TO artwork. Not part of daily data refresh.

Requires the versions in requirements-brand.txt; run from repository root.
Output is a reviewed brand revision, never a data boundary or filter.
"""
from pathlib import Path
import hashlib
import json
from html import escape
import shapely
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.ops import transform, unary_union
from pyproj import Transformer
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assets/brand'
MANIFEST = OUT / 'regions.json'
SOURCES = {
    'scarborough-council-boundary.geojson': '06cb43ee1b137938f6feb8dd9b355dcf819b8838',
    'scarborough-neighbourhoods.geojson': '14ba105712c753a8d1f47b9d00648381987dedf8',
}
LOCAL_CRS = '+proj=aeqd +lat_0=43.78 +lon_0=-79.20 +datum=WGS84 +units=m +no_defs'

def read_source(name):
    data = (ROOT / 'docs/data' / name).read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    if blob != SOURCES[name]:
        raise ValueError(f'{name}: source changed; review a new brand revision, do not auto-refresh')
    return json.loads(data)

def polygons(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    return [p for part in g.geoms for p in polygons(part)]

def build():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    projection = Transformer.from_crs('EPSG:4326', LOCAL_CRS, always_xy=True).transform
    council = read_source('scarborough-council-boundary.geojson')
    outer = shapely.set_precision(shapely.set_precision(transform(projection, shape(council['geometry'])), .001), 0)
    features = read_source('scarborough-neighbourhoods.geojson')['features']
    by_name = {f['properties']['AREA_NAME']: shapely.set_precision(shapely.set_precision(transform(projection, shape(f['geometry'])), .001), 0) for f in features}
    members = [n for r in manifest['regions'] for n in r['members']]
    assert len(members) == len(set(members)) == 31
    assert set(members) == set(by_name)
    assert outer.is_valid and all(g.is_valid for g in by_name.values())
    regions = [unary_union([by_name[n] for n in r['members']]).intersection(outer) for r in manifest['regions']]
    union = unary_union(regions)
    gap = outer.difference(union)
    overlap = sum(g.area for g in regions) - union.area
    # Tiny differences between independently published City datasets may be
    # reconciled for this decorative artwork only. Larger errors fail closed.
    assert gap.area / outer.area < .001, 'Material source mismatch; inspect rather than fabricate coverage'
    assert overlap / outer.area < .001, 'Material overlap; inspect source geometry'
    repaired = []
    occupied = Polygon()
    for g in regions:
        clean = g.difference(occupied)
        repaired.append(clean)
        occupied = unary_union([occupied, clean])
    for sliver in polygons(outer.difference(occupied)):
        lengths = [sliver.boundary.intersection(g.boundary).length for g in repaired]
        winner = max(range(len(repaired)), key=lambda i: (lengths[i], -sliver.distance(repaired[i]), -i))
        repaired[winner] = unary_union([repaired[winner], sliver])
    assert shapely.coverage_is_valid(repaired), 'Source partition requires topology review'
    assert outer.symmetric_difference(unary_union(repaired)).area < .01
    # Shared-edge simplification preserves topology. Keep the exact outer
    # boundary in this pass, then clip every region to one simplified outline.
    simplified = shapely.coverage_simplify(repaired, tolerance=40, simplify_boundary=False)
    outline = outer.simplify(40, preserve_topology=True)
    final = [g.intersection(outline) for g in simplified]
    # Fill tiny exterior-only simplification differences with nearest region.
    for sliver in polygons(outline.difference(unary_union(final))):
        lengths = [sliver.boundary.intersection(g.boundary).length for g in final]
        winner = max(range(len(final)), key=lambda i: (lengths[i], -sliver.distance(final[i]), -i))
        final[winner] = unary_union([final[winner], sliver])
    # Reassign sub-pixel detached fragments to their actual touching neighbour.
    # This changes decorative colour only; never discard land or source records.
    transfers=[]
    for i in range(len(final)):
        parts=sorted(polygons(final[i]),key=lambda p:p.area,reverse=True)
        for fragment in parts[1:]:
            assert fragment.area < 1000, 'Material disconnected group: revise membership'
            lengths=[fragment.boundary.intersection(g.boundary).length if j!=i else -1 for j,g in enumerate(final)]
            winner=max(range(len(final)),key=lambda j:(lengths[j],-j))
            assert lengths[winner]>0, str({'area':fragment.area,'bounds':fragment.bounds,'distances':[fragment.distance(g) for g in final],'boundary_lengths':lengths})
            final[i]=final[i].difference(fragment)
            final[winner]=unary_union([final[winner],fragment])
            transfers.append({'from':manifest['regions'][i]['name'],'to':manifest['regions'][winner]['name'],'area_m2':fragment.area})
    assert all(g.is_valid for g in final)
    assert all(len(polygons(g)) == 1 for g in final), 'Each decorative region must be contiguous'
    assert shapely.coverage_is_valid(final), 'Final clipped partition requires topology review'
    assert outline.symmetric_difference(unary_union(final)).area < .01
    assert abs(sum(g.area for g in final) - outline.area) < .01
    assert outer.hausdorff_distance(outline) <= 40.01
    # Projection is metric and north-up: one scale on both axes, y inverted
    # only because SVG's screen coordinates point down.
    x0, y0, x1, y1 = outer.bounds
    scale = 1000 / (y1 - y0)
    width = (x1 - x0) * scale
    def xy(x,y,z=None): return ((x-x0)*scale,(y1-y)*scale)
    def path(g):
        pieces = []
        for p in polygons(transform(xy,g)):
            for ring in [p.exterior, *p.interiors]:
                pieces.append('M'+' L'.join(f'{x:.3f},{y:.3f}' for x,y in ring.coords)+' Z')
        return ' '.join(pieces)
    silhouette = path(outline)
    fills = ''.join(f'<path d="{path(g)}" fill="{r["colour"]}" fill-rule="evenodd"/>' for g,r in zip(final,manifest['regions']))
    # Draw only actual shared internal edges; never stroke the coastline.
    edges = unary_union([final[i].boundary.intersection(final[j].boundary) for i in range(len(final)) for j in range(i)])
    def linepaths(g):
        if g.is_empty: return ''
        if g.geom_type in ('Point', 'MultiPoint'): return ''
        if g.geom_type in ('LineString','LinearRing'):
            return 'M'+' L'.join(f'{x:.3f},{y:.3f}' for x,y in transform(xy,g).coords)
        return ' '.join(linepaths(p) for p in g.geoms)
    border = linepaths(edges.simplify(5, preserve_topology=True))
    mark = f'<defs><clipPath id="land"><path d="{silhouette}"/></clipPath></defs><g clip-path="url(#land)">{fills}<path d="{border}" fill="none" stroke="#FFFFFF" stroke-width="9" stroke-linejoin="round" stroke-linecap="round"/></g>'
    description = 'North-up Scarborough Community Council silhouette with decorative groups of City neighbourhoods. Not official boundaries or data filters.'
    def svg(viewbox, body, title='Scarb.TO'):
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{description}</desc>{body}</svg>\n'
    vb = f'-24 -24 {width+48:.3f} 1048'
    (OUT/'scarbto-mark.svg').write_text(svg(vb,mark),encoding='utf-8')
    mark_dark=mark+f'<path d="{silhouette}" fill="none" stroke="#F8F5EA" stroke-width="9" stroke-linejoin="round"/>'
    (OUT/'scarbto-mark-dark.svg').write_text(svg(vb,mark_dark),encoding='utf-8')
    for name,colour in [('mono','#0F5132'),('light','#F8F5EA')]:
        (OUT/f'scarbto-mark-{name}.svg').write_text(svg(vb,f'<path d="{silhouette}" fill="{colour}"/>'),encoding='utf-8')
    # Same outline, no internal hairlines at 16 px. Square padded canvas.
    size=max(width,1000)+168
    left=(width-size)/2
    top=(1000-size)/2
    icon=f'<rect x="{left:.3f}" y="{top:.3f}" width="{size:.3f}" height="{size:.3f}" rx="170" fill="#0A3D2A"/><path d="{silhouette}" fill="#CFE6C2"/>'
    (OUT/'scarbto-icon.svg').write_text(svg(f'{left:.3f} {top:.3f} {size:.3f} {size:.3f}',icon),encoding='utf-8')
    # Outlined licensed lettering; no webfont or SVG text dependency.
    fontfile=OUT/'source/DMSans.ttf'
    assert hashlib.sha256(fontfile.read_bytes()).hexdigest() == '8cd08d97e89c24d0aa92edd2f0f4c8ee6195eee9b7c9f154865a58b02f0c1c0d'
    def kern(font, first, second):
        """Latin pair-advance kerning from instantiated GPOS kern features."""
        if 'GPOS' not in font: return 0
        table=font['GPOS'].table
        indices=set()
        for record in table.FeatureList.FeatureRecord:
            if record.FeatureTag == 'kern': indices.update(record.Feature.LookupListIndex)
        adjustment=0
        for index in sorted(indices):
            lookup=table.LookupList.Lookup[index]
            for sub in lookup.SubTable:
                if lookup.LookupType == 9:
                    if sub.ExtensionLookupType != 2: continue
                    sub=sub.ExtSubTable
                elif lookup.LookupType != 2: continue
                if first not in sub.Coverage.glyphs: continue
                value=None
                if sub.Format == 1:
                    pairs=sub.PairSet[sub.Coverage.glyphs.index(first)].PairValueRecord
                    value=next((p.Value1 for p in pairs if p.SecondGlyph == second),None)
                elif sub.Format == 2:
                    c1=sub.ClassDef1.classDefs.get(first,0)
                    c2=sub.ClassDef2.classDefs.get(second,0)
                    value=sub.Class1Record[c1].Class2Record[c2].Value1
                if value is not None:
                    adjustment+=getattr(value,'XAdvance',0)
                    break
        return adjustment
    def lettering(text, weight, target_height):
        font=instantiateVariableFont(TTFont(fontfile),{'wght':weight,'opsz':14},inplace=False)
        glyphs=font.getGlyphSet(); cmap=font.getBestCmap(); cursor=0; paths=[]
        names=[cmap[ord(c)] for c in text]
        for i,name in enumerate(names):
            if i: cursor+=kern(font,names[i-1],name)
            glyph=glyphs[name]; pen=SVGPathPen(glyphs); glyph.draw(pen)
            paths.append(f'<path transform="translate({cursor} 0)" d="{pen.getCommands()}"/>')
            cursor+=glyph.width
        s=target_height/font['head'].unitsPerEm
        return f'<g transform="scale({s} {-s})">'+''.join(paths)+'</g>',cursor*s
    word,wordwidth=lettering('Scarb.TO',800,170)
    tag,_=lettering('Scarborough. I looked into it.',400,37)
    for name,colour in [('scarbto-connected','#0A3D2A'),('scarbto-connected-light','#F8F5EA')]:
        symbol=mark_dark if name.endswith('-light') else mark
        body=f'<g transform="translate(12 12) scale(.29)">{symbol}</g><g fill="{colour}" transform="translate({width*.29+55:.3f} 175)">{word}</g><g fill="{colour}" transform="translate({width*.29+58:.3f} 245)">{tag}</g>'
        (OUT/f'{name}.svg').write_text(svg(f'0 0 {width*.29+wordwidth+85:.3f} 320',body),encoding='utf-8')
    report={'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'region_definition_sha256':hashlib.sha256(json.dumps(manifest['regions'],sort_keys=True).encode()).hexdigest(),'source_git_blobs':SOURCES,'crs':LOCAL_CRS,'fragment_colour_transfers':transfers,'precision_grid_m':.001,'source_feature_count':31,'region_count':len(regions),'source_gap_m2':gap.area,'source_overlap_m2':overlap,'outline_area_m2':outer.area,'simplification_tolerance_m':40,'outline_hausdorff_m':outer.hausdorff_distance(outline),'final_gap_m2':outline.symmetric_difference(unary_union(final)).area,'final_overlap_m2':sum(g.area for g in final)-outline.area,'region_components':[len(polygons(g)) for g in final],'region_component_areas_m2':[[p.area for p in polygons(g)] for g in final],'source_outline_bounds':outer.bounds,'render_scale':scale,'font_sha256':hashlib.sha256(fontfile.read_bytes()).hexdigest(),'tool_versions':{'shapely':shapely.__version__}}
    (OUT/'geometry-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__': build()
