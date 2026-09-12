// Enrol / verify faces for ARIA from still photos, headless (no camera needed).
//   node aria-enrol-faces.mjs <name> <photo-url-1> [photo-url-2 ...]
// Photos must be served by ARIA's backend (put them under macapp/Resources/enrol_tmp/
// and refer to them as ./enrol_tmp/x.jpg). The FIRST photo enrols; the rest are used
// to prove recognition (cross-photo match) and, if they match, added as extra samples.
import { chromium } from 'playwright';

const [name, ...photos] = process.argv.slice(2);
if (!name || !photos.length) { console.error('usage: node aria-enrol-faces.mjs <name> <photo> [more photos]'); process.exit(2); }

const browser = await chromium.launch({ headless: true, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage();
page.on('console', m => { if (/\[faces\]/.test(m.text())) console.log('  page:', m.text()); });
await page.goto('http://127.0.0.1:8080/hud/hud.html', { waitUntil: 'domcontentloaded' });
await page.waitForFunction(() => window.__ariaFaces && window.__ariaFaces.ready, null, { timeout: 90000 });

const result = await page.evaluate(async ({ name, photos }) => {
  const API = 'http://127.0.0.1:8080';
  const out = { name, photos: [] };
  const opts = new faceapi.TinyFaceDetectorOptions({ inputSize: 416, scoreThreshold: 0.3 });
  const describe = async (url) => {
    const img = await faceapi.fetchImage(url);
    const dets = await faceapi.detectAllFaces(img, opts).withFaceLandmarks().withFaceDescriptors();
    return { w: img.naturalWidth, h: img.naturalHeight, dets };
  };
  const roster = async () => (await (await fetch(API + '/assistant/faces/roster')).json()).people;
  const enrol = async (descs) => (await (await fetch(API + '/assistant/faces/enrol', { method: 'POST',
    headers: { 'content-type': 'application/json' }, body: JSON.stringify({ name, descriptors: descs.map(d => Array.from(d)) }) })).json());

  let first = true;
  for (const url of photos) {
    const { w, h, dets } = await describe(url);
    const rec = { url, w, h, faces: dets.map(d => +d.detection.score.toFixed(2)) };
    if (dets.length === 1) {
      const people = await roster();
      const mine = people.find(p => p.name.toLowerCase() === name.toLowerCase());
      if (mine && mine.descs.length) {
        const m = new faceapi.FaceMatcher([new faceapi.LabeledFaceDescriptors(mine.name, mine.descs.map(d => new Float32Array(d)))], 0.5)
          .findBestMatch(dets[0].descriptor);
        rec.match = { label: m.label, distance: +m.distance.toFixed(3) };
        if (m.label !== 'unknown') rec.enrolled = await enrol([dets[0].descriptor]);
      } else if (first) {
        rec.enrolled = await enrol([dets[0].descriptor]);
      }
    }
    first = false;
    out.photos.push(rec);
  }
  out.roster = (await roster()).map(p => ({ name: p.name, samples: p.descs.length }));
  return out;
}, { name, photos });

console.log(JSON.stringify(result, null, 2));
await browser.close();
