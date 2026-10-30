// Offline publication preparation. No renderer or star catalog is required.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir, copyFile, realpath } from 'node:fs/promises';
import { execFileSync, spawnSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { FloatType } from 'three';
import { EXRLoader } from 'three/addons/loaders/EXRLoader.js';

const [input, output] = process.argv.slice(2);
assert.ok(input && output, 'Usage: node prepare.mjs <starmap_2020_4k.exr> <new-output-directory>');
const recipe = dirname(fileURLToPath(import.meta.url));
const git = (...args) => execFileSync('git', args, { cwd: recipe, encoding: 'utf8' }).trim();
assert.equal(git('status', '--porcelain'), '', 'Prepare release artifacts from a clean committed checkout.');
const commit = git('rev-parse', 'HEAD');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const threePackage = fileURLToPath(new URL('../package.json', import.meta.resolve('three')));
assert.equal(await realpath(threePackage), resolve(recipe, 'node_modules/three/package.json'),
  'Install the public locked Three.js package beside this recipe with npm ci.');
assert.equal(JSON.parse(await readFile(threePackage, 'utf8')).version, '0.170.0');
const source = await readFile(input);
assert.equal(hash(source), '69b841cd048c2ef35543eb1c5819b322530e78aa4b0cab97ec1de3ef56a4ddcd',
  'Source differs from the admitted NASA Deep Star Maps 2020 celestial 4k EXR.');
const map = new EXRLoader().setDataType(FloatType).parse(
  source.buffer.slice(source.byteOffset, source.byteOffset + source.byteLength));
assert.equal(map.width, 4096); assert.equal(map.height, 2048);
const pixels = Buffer.alloc(map.width * map.height * 3);
for (let y = 0; y < map.height; y++) for (let x = 0; x < map.width; x++) {
  // EXRLoader returns GPU rows bottom first; the image stores north first.
  const from = ((map.height - 1 - y) * map.width + x) * 4;
  const to = (y * map.width + x) * 3;
  for (let channel = 0; channel < 3; channel++) {
    assert.ok(Number.isFinite(map.data[from + channel]), 'Non-finite source sample.');
    const linear = Math.max(0, Math.min(1, map.data[from + channel]));
    const srgb = linear <= 0.0031308 ? 12.92 * linear : 1.055 * linear ** (1 / 2.4) - 0.055;
    pixels[to + channel] = Math.round(255 * srgb);
  }
}
// Refuse to replace a previous product, including one from another encoder.
await mkdir(output);
const filename = 'deep-star-map-2020-4k.webp';
const args = ['-hide_banner', '-loglevel', 'error', '-n', '-f', 'rawvideo', '-pixel_format', 'rgb24',
  '-video_size', `${map.width}x${map.height}`, '-i', 'pipe:0', '-frames:v', '1', '-c:v', 'libwebp',
  '-quality', '90', '-compression_level', '6', resolve(output, filename)];
const encoded = spawnSync('ffmpeg', args, { input: pixels, encoding: 'utf8' });
assert.equal(encoded.status, 0, encoded.stderr);
const payload = await readFile(resolve(output, filename));
const product = {
  formatVersion: 1, release: '20261017.1', productId: 'deep-star-maps-2020-celestial-4k',
  source: { page: 'https://svs.gsfc.nasa.gov/4851/',
    url: 'https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004851/starmap_2020_4k.exr',
    sha256: hash(source), bytes: source.length },
  credit: 'NASA/Goddard Space Flight Center Scientific Visualization Studio; Gaia DR2: ESA/Gaia/DPAC',
  projection: { type: 'plate-carree', frame: 'ICRF/J2000', centreRaDegrees: 0,
    raIncreases: 'left', north: 'top', width: map.width, height: map.height },
  representation: 'Display imagery; clamped and lossy, not scientific photometry or a selectable star catalog.',
  preparation: { repository: 'https://github.com/Found-in-Space/catalogs', commit,
    recipe: 'publications/20261017.1/recipe/prepare.mjs',
    scriptSha256: hash(await readFile(fileURLToPath(import.meta.url))),
    lockfileSha256: hash(await readFile(resolve(recipe, 'package-lock.json'))),
    three: '0.170.0', node: process.version,
    ffmpeg: execFileSync('ffmpeg', ['-version'], { encoding: 'utf8' }).split('\n')[0],
    transform: 'linear RGB clamped to [0,1], IEC sRGB transfer, nearest 8-bit RGB; no resizing or exposure change; reverse EXRLoader rows',
    encoding: 'WebP, quality 90, compression level 6' },
  license: { image: 'NASA SVS public-domain usage policy, subject to noted third-party rights; see LICENSE.txt and NOTICE.md',
    policy: 'https://svs.gsfc.nasa.gov/help/', notice: 'NOTICE.md' },
  output: { path: filename, sha256: hash(payload), bytes: payload.length,
    contentType: 'image/webp', colorSpace: 'sRGB' },
};
await writeFile(resolve(output, 'product.json'), JSON.stringify(product, null, 2) + '\n');
for (const name of ['LICENSE.txt', 'NOTICE.md']) await copyFile(resolve(recipe, '..', name), resolve(output, name));
const names = [filename, 'product.json', 'LICENSE.txt', 'NOTICE.md'].sort();
const checksums = await Promise.all(names.map(async name => `${hash(await readFile(resolve(output, name)))}  ${name}\n`));
await writeFile(resolve(output, 'checksums.sha256'), checksums.join(''));
console.log(JSON.stringify(product.output));
