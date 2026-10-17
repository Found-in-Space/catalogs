// Gnomonic caps in the same ICRF/J2000 frame as the source map.
export const CAP_SIZE = 1024;
export const CAP_HALF_ANGLE_DEGREES = 35;
export const CAP_EXTENT = Math.tan(CAP_HALF_ANGLE_DEGREES * Math.PI / 180);

// Pixel centres; +X is right and +Y is top in both cap images.
export function capDirection(x, y, size, hemisphere) {
  return { x: (2 * (x + 0.5) / size - 1) * CAP_EXTENT,
    y: (1 - 2 * (y + 0.5) / size) * CAP_EXTENT, z: hemisphere };
}

// EXRLoader stores rows bottom first. Interpolate in linear RGB before the
// display transfer, with longitude wrapping and latitude clamped at the poles.
export function sampleLinearRgb(map, { x, y, z }) {
  const u = 0.5 - Math.atan2(y, x) / (2 * Math.PI);
  const v = 0.5 + Math.atan2(z, Math.hypot(x, y)) / Math.PI;
  const px = u * map.width - 0.5, py = v * map.height - 0.5;
  const left = Math.floor(px), bottom = Math.floor(py);
  const fx = px - left, fy = py - bottom;
  const sample = (column, row, channel) => map.data[(
    Math.max(0, Math.min(map.height - 1, row)) * map.width +
    ((column % map.width) + map.width) % map.width) * 4 + channel];
  return [0, 1, 2].map(channel =>
    (1 - fy) * ((1 - fx) * sample(left, bottom, channel) + fx * sample(left + 1, bottom, channel)) +
    fy * ((1 - fx) * sample(left, bottom + 1, channel) + fx * sample(left + 1, bottom + 1, channel)));
}
