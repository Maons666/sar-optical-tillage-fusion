// =====================================================================
//  Till v0.9  —  §4.5 Coverage Analysis (ASYNC EXPORT, FIXED)
//
//  How to use:
//    1. Paste into the GEE Code Editor and press Run.
//    2. Two Tasks appear in the right panel — click RUN on each.
//    3. CSVs land in Drive/GEE_exports/ when finished.
//    4. Y% = mean(fraction) × 100 from the S2 CSV
//       X% = mean(fraction) × 100 from the fused CSV
//       gap = X − Y
//
//  Bug fix vs previous version:
//    .count().gt(0) returns MASKED at pixels with no observations,
//    not 0.  That made every reducer trivially produce 1.0.  All
//    obs-availability tests now go .count().gt(0).unmask(0) so
//    pixels with no obs explicitly become 0.
//
//  Region:  Whole Nebraska, corn + soybean cropland (CDL 2024)
//  Period:  2025-05-01 → 2025-06-30  (9 × 7-day windows)
// =====================================================================

// ---- 1. AOI -----------------------------------------------------------
var aoi = ee.FeatureCollection('TIGER/2018/States')
            .filter(ee.Filter.eq('NAME', 'Nebraska'));

// ---- 2. Cropland mask: corn (1) + soybean (5) from CDL 2024 ----------
var cdl = ee.Image('USDA/NASS/CDL/2024').select('cropland');
var cropMask = cdl.eq(1).or(cdl.eq(5)).selfMask();

// ---- 3. Weeks ---------------------------------------------------------
var startDate = ee.Date('2025-05-01');
var endDate   = ee.Date('2025-06-30');
var nWeeks    = endDate.difference(startDate, 'week').round();
var weeks     = ee.List.sequence(0, nWeeks.subtract(1));

// ---- 4. Sentinel-2 with SCL cloud mask --------------------------------
function maskS2(img) {
  var scl = img.select('SCL');
  // Clear-sky SCL classes: 4 vegetation, 5 bare soil, 6 water,
  //                        7 unclassified, 11 snow / ice
  var clear = scl.eq(4).or(scl.eq(5)).or(scl.eq(6))
                .or(scl.eq(7)).or(scl.eq(11));
  return img.updateMask(clear)
            .copyProperties(img, ['system:time_start']);
}
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
           .filterBounds(aoi).filterDate(startDate, endDate)
           .map(maskS2).select('B4');

// ---- 5. Sentinel-1 GRD (all-weather) ---------------------------------
var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
           .filterBounds(aoi).filterDate(startDate, endDate)
           .filter(ee.Filter.eq('instrumentMode', 'IW'))
           .filter(ee.Filter.listContains(
              'transmitterReceiverPolarisation', 'VV'))
           .select('VV');

// ---- 6. Weekly coverage helpers --------------------------------------
//  Key fix: .unmask(0) right after .count().gt(0) so pixels with no
//  observation become explicit zeros (not masked).
var REDUCE_OPTS = {
  reducer:   ee.Reducer.mean(),
  geometry:  aoi,
  scale:     500,
  tileScale: 8,
  maxPixels: 1e10,
  bestEffort: true
};

function weeklyOptical(wIdx) {
  var w  = ee.Number(wIdx);
  var ws = startDate.advance(w, 'week');
  var we = ws.advance(7, 'day');
  var has = s2.filterDate(ws, we)
              .count().gt(0).unmask(0)               // <-- FIX
              .updateMask(cropMask).rename('hasObs');
  return ee.Feature(null, {
    week:      w,
    weekStart: ws.format('YYYY-MM-dd'),
    source:    'S2 only',
    fraction:  has.reduceRegion(REDUCE_OPTS).get('hasObs')
  });
}

function weeklyFused(wIdx) {
  var w  = ee.Number(wIdx);
  var ws = startDate.advance(w, 'week');
  var we = ws.advance(7, 'day');
  var s2Has = s2.filterDate(ws, we).count().gt(0).unmask(0);  // <-- FIX
  var s1Has = s1.filterDate(ws, we).count().gt(0).unmask(0);  // <-- FIX
  var has   = s2Has.or(s1Has)
                   .updateMask(cropMask).rename('hasObs');
  return ee.Feature(null, {
    week:      w,
    weekStart: ws.format('YYYY-MM-dd'),
    source:    'fused (S2 ∪ S1)',
    fraction:  has.reduceRegion(REDUCE_OPTS).get('hasObs')
  });
}

var s2Weekly    = ee.FeatureCollection(weeks.map(weeklyOptical));
var fusedWeekly = ee.FeatureCollection(weeks.map(weeklyFused));

// ---- 7. Async export tasks -------------------------------------------
Export.table.toDrive({
  collection:  s2Weekly,
  description: 's2_weekly_coverage_nebraska_2025',
  folder:      'GEE_exports',
  fileFormat:  'CSV',
  selectors:   ['week', 'weekStart', 'source', 'fraction']
});

Export.table.toDrive({
  collection:  fusedWeekly,
  description: 'fused_weekly_coverage_nebraska_2025',
  folder:      'GEE_exports',
  fileFormat:  'CSV',
  selectors:   ['week', 'weekStart', 'source', 'fraction']
});

print('---------------------------------------------------------------');
print('TWO EXPORT TASKS QUEUED.');
print(' • Open the "Tasks" tab on the right side of the Code Editor.');
print(' • Click "RUN" on each task.');
print(' • Both CSVs will appear in Drive/GEE_exports/ when finished.');
print(' • Mean of the "fraction" column × 100  =  weekly coverage %.');
print('---------------------------------------------------------------');

// ---- 8. Optional live preview (no reducers — render only) -----------
Map.centerObject(aoi, 6);
Map.addLayer(cropMask, {palette: ['cccccc'], opacity: 0.3},
             'corn + soy cropland (CDL 2024)');
Map.addLayer(s2.count().rename('s2_obs').updateMask(cropMask).clip(aoi),
             {min: 0, max: 12,
              palette: ['red','orange','yellow','lightgreen','green']},
             'S2 cloud-free obs count');
Map.addLayer(s1.count().rename('s1_obs').updateMask(cropMask).clip(aoi),
             {min: 0, max: 25,
              palette: ['lightblue','steelblue','darkblue']},
             'S1 obs count');
