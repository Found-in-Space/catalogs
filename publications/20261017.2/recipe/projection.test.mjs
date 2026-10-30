import assert from 'node:assert/strict';
import { test } from 'node:test';
import { capDirection, sampleLinearRgb, CAP_EXTENT } from './projection.mjs';

test('caps centre on their poles and retain a common X/Y orientation', () => {
  assert.deepEqual(capDirection(1, 1, 3, 1), { x: 0, y: 0, z: 1 });
  assert.deepEqual(capDirection(1, 1, 3, -1), { x: 0, y: 0, z: -1 });
  for (const hemisphere of [-1, 1]) {
    assert.ok(capDirection(2, 1, 3, hemisphere).x > 0);
    assert.ok(capDirection(1, 0, 3, hemisphere).y > 0);
    const d = capDirection(0, 0, 1024, hemisphere);
    assert.ok(Math.atan2(Math.abs(d.z), Math.hypot(d.x, d.y)) * 180 / Math.PI < 55);
    assert.ok(CAP_EXTENT > Math.tan(30 * Math.PI / 180));
  }
});

test('source sampling wraps the RA seam and clamps both latitude edges', () => {
  const map = { width: 4, height: 2, data: new Float32Array(4 * 2 * 4) };
  for (let y = 0; y < 2; y++) for (let x = 0; x < 4; x++) {
    const offset = (y * 4 + x) * 4;
    map.data.set([x, y, 0.25, 1], offset);
  }
  // The seam lies halfway between the final and first columns.
  assert.deepEqual(sampleLinearRgb(map, { x: -1, y: 0, z: 0 }), [1.5, 0.5, 0.25]);
  for (const z of [-1, 1]) {
    const pixel = sampleLinearRgb(map, { x: 0, y: 0, z });
    assert.equal(pixel[1], z > 0 ? 1 : 0);
    assert.equal(pixel[2], 0.25);
  }
  const nearA = sampleLinearRgb(map, { x: -1, y: 1e-9, z: 0 });
  const nearB = sampleLinearRgb(map, { x: -1, y: -1e-9, z: 0 });
  assert.ok(Math.abs(nearA[0] - nearB[0]) < 1e-8);
});
