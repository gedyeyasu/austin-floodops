// Synthetic lifecycle benchmark. Provenance and reproduction are documented in docs/INCIDENT_AREA_TASK.md.
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const sample = {type:'Polygon',coordinates:[[[-97.75,30.26],[-97.73,30.26],[-97.73,30.28],[-97.75,30.26]]]};
  let map, preview, drawing = false, points = [], mode = 'draw', settle, ready = false, session = 0;
  let records = [], selectedId = null, requestId, saving = false;
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

  async function api(path, options) {
    const response = await fetch(path, options);
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Use a valid, closed GeoJSON Polygon with at least three vertices.');
    return data;
  }
  function renderRecords() {
    $('area-list').replaceChildren();
    if (!records.length) $('area-list').textContent = 'No saved exercise areas.';
    for (const area of records) {
      const li = document.createElement('li'), button = document.createElement('button');
      button.textContent = area.name;
      button.setAttribute('aria-pressed', String(area.id === selectedId));
      button.onclick = () => { selectedId = area.id; renderRecords(); };
      li.append(button); $('area-list').append(li);
    }
    const selected = records.find(area => area.id === selectedId);
    $('selected-area').replaceChildren();
    if (selected) {
      const title = document.createElement('h3'), details = document.createElement('pre');
      title.textContent = selected.name; details.textContent = JSON.stringify(selected.geometry, null, 2);
      $('selected-area').append(title, details);
    } else $('selected-area').textContent = 'No area selected.';
  }
  async function refresh() { records = await api('/api/exercise-areas'); renderRecords(); }
  function switchMode(next) {
    mode = next; drawing = next === 'draw' && ready;
    $('draw-mode').setAttribute('aria-pressed', String(next === 'draw'));
    $('upload-mode').setAttribute('aria-pressed', String(next === 'upload'));
    $('draw-pane').hidden = next !== 'draw'; $('upload-pane').hidden = next !== 'upload';
    if (map && next === 'draw') map.invalidateSize();
    $('map-progress').textContent = next === 'upload' ? 'Upload mode selected.' : ready ? 'Map ready — click to draw the boundary.' : 'Preparing map…';
  }
  function resetBoundary() {
    points = []; if (preview) preview.remove(); preview = null;
    $('point-count').textContent = '0 vertices';
  }
  function createMap() {
    if (!window.L) throw new Error('Leaflet could not load. Check your connection and reload.');
    map = L.map('area-map', {attributionControl:false});
    const Grid = L.GridLayer.extend({createTile(coords) {
      const tile = L.DomUtil.create('div', 'coordinate-tile');
      tile.textContent = `LOCAL GRID · ${coords.z}/${coords.x}/${coords.y}`;
      return tile;
    }});
    new Grid().addTo(map);
    map.on('click', event => {
      if (!drawing) return;
      points.push([event.latlng.lng, event.latlng.lat]);
      if (preview) preview.remove();
      preview = L.polygon(points.map(p => [p[1],p[0]]), {color:'#7cf7ad'}).addTo(map);
      $('point-count').textContent = `${points.length} vertices`;
    });
    // Deterministic stand-in for asynchronous initial view configuration.
    sleep(2500).then(() => map.setView([30.2672,-97.7431], 12));
  }
  async function prepareMap(opening) {
    if (!map) createMap();
    // Intentional task defect: load fires only once, but reopening waits again.
    await new Promise(resolve => map.once('load', resolve));
    await sleep(800);
    if (opening !== session || !$('area-dialog').open) return;
    map.invalidateSize();
    ready = true;
    switchMode(mode);
  }
  function openDialog() {
    const opening = ++session;
    const completion = new Promise(resolve => { settle = resolve; });
    requestId = crypto.randomUUID(); saving = false; ready = false;
    $('area-form').reset(); $('save-area').disabled = false;
    $('form-error').textContent = ''; resetBoundary(); switchMode('draw');
    $('area-dialog').showModal();
    prepareMap(opening).catch(error => {
      if (opening === session && $('area-dialog').open) $('map-progress').textContent = error.message;
    });
    return completion;
  }
  function finish(result) {
    const resolve = settle;
    settle = undefined;
    ++session;
    $('area-dialog').close(); drawing = false; ready = false;
    if (resolve) resolve(result);
  }
  function cancel() {
    if (saving) return;
    finish(null);
  }
  $('create-area').onclick = async () => {
    $('create-area').disabled = true;
    $('workspace-status').textContent = 'Waiting for incident area…';
    try {
      const saved = await openDialog();
      if (saved) selectedId = saved.id;
      await refresh();
      $('workspace-status').textContent = saved ? `Selected ${saved.name}.` : 'Creation cancelled.';
    } catch (error) { $('workspace-status').textContent = error.message; }
    finally { $('create-area').disabled = false; }
  };
  $('refresh-areas').onclick = () => refresh().catch(error => { $('workspace-status').textContent = error.message; });
  $('draw-mode').onclick = () => switchMode('draw');
  $('upload-mode').onclick = () => switchMode('upload');
  $('load-sample').onclick = () => { $('area-json').value = JSON.stringify(sample, null, 2); };
  $('area-file').onchange = async event => {
    const file = event.target.files[0]; if (!file) return;
    if (file.size > 100000) { $('form-error').textContent = 'Use a file smaller than 100 KB.'; return; }
    $('area-json').value = await file.text();
  };
  $('clear-boundary').onclick = resetBoundary;
  $('close-area').onclick = cancel; $('cancel-area').onclick = cancel;
  $('area-dialog').addEventListener('cancel', event => { event.preventDefault(); cancel(); });
  $('area-form').onsubmit = async event => {
    event.preventDefault(); if (saving) return;
    $('form-error').textContent = '';
    try {
      let geometry;
      if (mode === 'upload') {
        const parsed = JSON.parse($('area-json').value);
        geometry = parsed.type === 'Feature' ? parsed.geometry : parsed;
      } else {
        if (points.length < 3) throw new Error('Click at least three points on the map.');
        geometry = {type:'Polygon', coordinates:[[...points,points[0]]]};
      }
      saving = true; $('save-area').disabled = true;
      const saved = await api('/api/exercise-areas', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:requestId,name:$('area-name').value,geometry})});
      finish(saved);
    } catch (error) { $('form-error').textContent = error.message; }
    finally { saving = false; $('save-area').disabled = false; }
  };
  refresh().catch(error => { $('workspace-status').textContent = error.message; });
})();
