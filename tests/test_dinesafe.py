import csv
import io
import json
import tempfile
import subprocess
import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
from update_dinesafe import (DataError, build_snapshot, date_string, get_resources, in_geometry,
    make_activity, normalise, atomic_write, prepare_activity_archives, reconcile_activity_history)


def polygon(w,s,e,n):
    return {'type':'Polygon','coordinates':[[[w,s],[e,s],[e,n],[w,n],[w,s]]]}


def shapefile(names):
    return {'type':'FeatureCollection', 'features':[
        {'type':'Feature','properties':{'AREA_NAME':name},'geometry':geometry} for name,geometry in names]}


def wards():
    return shapefile([(f'Scarborough Ward {i+1}', polygon(-79.45+(i%3)*.1,43.70+(i//3)*.1,-79.35+(i%3)*.1,43.80+(i//3)*.1)) for i in range(6)])


def neighbourhoods():
    return shapefile([('Agincourt',polygon(-79.45,43.70,-79.35,43.80)),('Port Union',polygon(-79.25,43.80,-79.15,43.90))])


def rows_as_csv(rows):
    b=io.StringIO()
    cols=['ESTABLISHMENT_ID','ESTABLISHMENT_NAME','ESTABLISHMENT_ADDRESS','ESTABLISHMENTTYPE','ESTABLISHMENT_STATUS','INSPECTION_DATE','LATITUDE','LONGITUDE']
    wr=csv.DictWriter(b,fieldnames=cols)
    wr.writeheader()
    wr.writerows(rows)
    return b.getvalue().encode('utf-8-sig')


def item(id, name, status, date, lat=43.74,lon=-79.40):
    return dict(ESTABLISHMENT_ID=id,ESTABLISHMENT_NAME=name,ESTABLISHMENT_ADDRESS='123 Main St',ESTABLISHMENTTYPE='Restaurant',ESTABLISHMENT_STATUS=status,INSPECTION_DATE=date,LATITUDE=lat,LONGITUDE=lon)


class IngestionTests(unittest.TestCase):
    def test_latest_inspection_and_exclusion_and_names(self):
        csv_data=rows_as_csv([item('10','Northern Café','Pass','2026-10-01'),item('10','Northern Café','Conditional Pass','2026-10-18'),item('11','East, Diner','Closed','2026-10-20',43.84,-79.2),item('99','Outside','Pass','2026-10-15',43.60,-79.6)])
        items,stats,neighbourhoods_geo=normalise(csv_data,wards(),neighbourhoods(),minimum=1)
        self.assertEqual(len(items),2)
        self.assertEqual(items[1]['status'],'Conditional Pass')
        self.assertEqual(items[0]['status'],'Closed')
        self.assertEqual(stats['source_rows'],4)
        self.assertEqual(stats['scarborough_establishments'],2)
        self.assertEqual(len(neighbourhoods_geo['features']),2)

    def test_current_city_schema_separates_finding_from_category_and_cleans_address(self):
        source = io.StringIO()
        columns = ['estId', 'estName', 'address', 'typeDesc', 'inspectionStatus',
                   'inspectionDate', 'latitude', 'longitude']
        writer = csv.DictWriter(source, fieldnames=columns)
        writer.writeheader()
        writer.writerow(dict(estId='10', estName='A Diner', address='123 Main St None M1A 1A1',
                             typeDesc='FAIL TO MAINTAIN EQUIPMENT - SEC. 20',
                             inspectionStatus='Pass', inspectionDate='2026-10-25',
                             latitude=43.74, longitude=-79.40))
        writer.writerow(dict(estId='11', estName='B Diner', address='None',
                             typeDesc='None', inspectionStatus='Conditional Pass',
                             inspectionDate='2026-10-25', latitude=43.74, longitude=-79.40))
        entries, _, _ = normalise(source.getvalue().encode('utf-8'), wards(), neighbourhoods(), minimum=1)
        found = {entry['id']: entry for entry in entries}
        self.assertEqual(found['10']['address'], '123 Main St M1A 1A1')
        self.assertEqual(found['10']['type'], '')
        self.assertEqual(found['10']['inspection_detail'], 'FAIL TO MAINTAIN EQUIPMENT - SEC. 20')
        self.assertEqual(found['11']['address'], '')
        self.assertEqual(found['11']['type'], '')
        self.assertEqual(found['11']['inspection_detail'], '')

    def test_legacy_category_is_not_treated_as_inspection_finding(self):
        entries, _, _ = normalise(rows_as_csv([item('1', 'Diner', 'Pass', '2026-10-20')]),
                                  wards(), neighbourhoods(), minimum=1)
        self.assertEqual(entries[0]['type'], 'Restaurant')
        self.assertEqual(entries[0]['inspection_detail'], '')

    def test_geospatial_holes_and_boundary_points(self):
        geom={'type':'Polygon','coordinates':[[[0,0],[3,0],[3,3],[0,3],[0,0]],[[1,1],[2,1],[2,2],[1,2],[1,1]]]}
        self.assertTrue(in_geometry(.5,.5,geom))
        self.assertFalse(in_geometry(1.5,1.5,geom))
        self.assertTrue(in_geometry(0,1.5,geom))
        self.assertFalse(in_geometry(4,1.5,geom))

    def test_schema_drift_fails_closed(self):
        csv_data=b'ESTABLISHMENT_ID,ESTABLISHMENT_NAME,LATITUDE,LONGITUDE\n1,Diner,43.74,-79.40\n'
        with self.assertRaisesRegex(DataError,'required columns'):
            normalise(csv_data,wards(),neighbourhoods(),minimum=1)

    def test_unknown_status_not_silently_published(self):
        csv_data=rows_as_csv([item('1','Diner','Not Inspected','2026-10-20')])
        with self.assertRaisesRegex(DataError,'Unrecognised'):
            normalise(csv_data,wards(),neighbourhoods(),minimum=1)

    def test_latest_same_date_conflict_held(self):
        csv_data=rows_as_csv([item('1','Diner','Pass','2026-10-20'),item('1','Diner','Closed','2026-10-20')])
        with self.assertRaisesRegex(DataError,'Conflicting'):
            normalise(csv_data,wards(),neighbourhoods(),minimum=1)

    def test_unexpected_drop_not_published(self):
        csv_data=rows_as_csv([item('1','Diner','Pass','2026-10-20')])
        previous={'ready':True,'establishments':[{'id':str(i)} for i in range(10)],'activity':[]}
        with self.assertRaisesRegex(DataError,'mass deletion'):
            build_snapshot(csv_data,wards(),neighbourhoods(),previous=previous,source_url='fixture',last_refreshed=None,now=datetime.now(timezone.utc),minimum=1)

    def test_baseline_not_misrepresented_as_new(self):
        csv_data=rows_as_csv([item('1','Diner','Pass','2026-10-10')])
        now=datetime(2026,10,24,tzinfo=timezone.utc)
        first,_=build_snapshot(csv_data,wards(),neighbourhoods(),previous=None,source_url='fixture',last_refreshed=None,now=now,minimum=1)
        self.assertTrue(first['ready'])
        self.assertEqual(first['activity'],[])
        updated=rows_as_csv([item('1','Diner','Conditional Pass','2026-10-20'),item('2','Cafe','Pass','2026-10-20')])
        second,_=build_snapshot(updated,wards(),neighbourhoods(),previous=first,source_url='fixture',last_refreshed=None,now=now,minimum=1)
        self.assertEqual({e['kind'] for e in second['activity']},{'status_changed','first_seen'})
        third,_=build_snapshot(updated,wards(),neighbourhoods(),previous=second,source_url='fixture',last_refreshed=None,now=now,minimum=1)
        self.assertEqual(len(third['activity']),2)

    def test_csv_resource_discovery(self):
        result={'success':True,'result':{'last_refreshed':'2026-10-24','resources':[
            {'name':'Dinesafe Historical Data','format':'ZIP','url':'https://city.test/archive.zip'},
            {'name':'Dinesafe.csv','format':'CSV','url':'https://city.test/dinesafe.csv'}]}}
        self.assertEqual(get_resources(result),('https://city.test/dinesafe.csv','2026-10-24'))
        with self.assertRaisesRegex(DataError,'No HTTPS'):
            get_resources({'success':True,'result':{'resources':[{'name':'old','format':'ZIP','url':'https://city.test/x'}]}})

    def test_monthly_change_archives_are_resumable_append_only_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            first = {'id': 'event-1', 'detected_at': '2026-10-27T15:54:39+00:00',
                     'source_url': 'https://open.toronto.ca/dataset/dinesafe/',
                     'address': '123 Main St M1A 1A1'}
            updates = prepare_activity_archives(output, [first])
            self.assertEqual(len(updates), 1)
            self.assertEqual(updates[0][0].name, '2026-10.json')
            for path, content in updates:
                atomic_write(path, content)
            self.assertEqual(prepare_activity_archives(output, [first]), [])

            corrected = {**first, 'address': 'Different value'}
            second = {'id': 'event-2', 'detected_at': '2026-10-28T08:00:00+00:00',
                      'source_url': first['source_url']}
            updates = prepare_activity_archives(output, [corrected, second])
            self.assertEqual(len(updates), 1)
            self.assertEqual([r['id'] for r in json.loads(updates[0][1])['events']],
                             ['event-1', 'event-2'])
            self.assertEqual(json.loads(updates[0][1])['events'][0]['address'],
                             first['address'], 'Existing observed events remain immutable')
            for path, content in updates:
                atomic_write(path, content)
            self.assertEqual(prepare_activity_archives(output, []), [],
                             'Later absence from the 365-day window does not remove archives')

            bad = output/'history'/'2026-11.json'
            atomic_write(bad, b'{"schema_version":2,"events":[]}')
            november = {**second, 'id': 'event-3', 'detected_at': '2026-11-01T12:00:00Z'}
            with self.assertRaisesRegex(DataError, 'Invalid existing activity archive'):
                prepare_activity_archives(output, [november])

    def test_cross_month_crash_retry_preserves_first_observation_once(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            first = {'id': 'stable-event', 'detected_at': '2026-10-31T23:59:50+00:00',
                     'source_url': 'https://open.toronto.ca/dataset/dinesafe/',
                     'establishment_id': '123', 'status': 'Pass'}
            # Simulate a process that wrote the October archive then crashed
            # before replacing snapshot.json.
            for path, content in prepare_activity_archives(output, [first]):
                atomic_write(path, content)

            retried = {**first, 'detected_at': '2026-11-01T00:00:10+00:00'}
            reconciled = reconcile_activity_history(output, [retried])
            self.assertEqual(reconciled, [first])
            self.assertEqual(prepare_activity_archives(output, reconciled), [])
            self.assertFalse((output/'history'/'2026-11.json').exists())
            archive = json.loads((output/'history'/'2026-10.json').read_text(encoding='utf-8'))
            self.assertEqual([event['id'] for event in archive['events']], ['stable-event'])
            self.assertEqual(archive['events'][0]['detected_at'], first['detected_at'])

    def test_date_formats_are_explicit(self):
        self.assertEqual(date_string('20261024'),'2026-10-24')
        self.assertEqual(date_string('2026-10-24T12:00:00'),'2026-10-24')
        self.assertEqual(date_string('10/24/2026'),'2026-10-24')
        self.assertIsNone(date_string('invalid'))

    def test_atomic_replace(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'nested'/'data.json'
            atomic_write(path,b'one')
            atomic_write(path,b'two')
            self.assertEqual(path.read_bytes(),b'two')
            self.assertEqual(len(list(path.parent.glob('.stage-*'))),0)

    def test_offline_cli_publication_and_failed_refresh_preserves_baseline(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'wards.geojson').write_text(json.dumps(wards()))
            (root/'neighbours.geojson').write_text(json.dumps(neighbourhoods()))
            feed=root/'feed.csv'
            feed.write_bytes(rows_as_csv([item('1','Working Diner','Pass','2026-10-20')]))
            cmd=[sys.executable, str(Path(__file__).resolve().parent.parent/'scripts'/'update_dinesafe.py'),
                '--csv',str(feed),'--wards',str(root/'wards.geojson'),
                '--neighbourhoods',str(root/'neighbours.geojson'),
                '--output',str(root/'published'),'--minimum','1']
            ok=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(ok.returncode,0,ok.stderr)
            snap=root/'published'/'snapshot.json'
            baseline=snap.read_bytes()
            self.assertEqual(json.loads(baseline)['establishments'][0]['name'],'Working Diner')
            report=(root/'published'/'establishments.csv').read_text(encoding='utf-8-sig')
            self.assertIn('https://open.toronto.ca/open-data-licence/',report)
            self.assertIn('inspection_detail',report.splitlines()[0])
            feed.write_bytes(rows_as_csv([item('1','Working Diner','Unknown','2026-10-22')]))
            blocked=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(blocked.returncode,0)
            self.assertIn('NOT PUBLISHED',blocked.stderr)
            self.assertEqual(snap.read_bytes(),baseline)


if __name__=='__main__':
    unittest.main()
