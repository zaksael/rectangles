const isObject = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v)

// The differences in key structure between a real payload and a typed exemplar of the same shape, one line each (empty when they agree).
// Objects must carry the same keys; arrays are compared by their first element; a null or empty array on either side ends the walk there.
export function shapeDiff(real: unknown, expected: unknown, path = '$'): string[] {
  if (isObject(real) && isObject(expected)) {
    return [...new Set([...Object.keys(real), ...Object.keys(expected)])].flatMap((key) => {
      if (!(key in real)) return [`${path}.${key}: in the TS shape, not sent by the server`]
      if (!(key in expected)) return [`${path}.${key}: sent by the server, not in the TS shape`]
      return shapeDiff(real[key], expected[key], `${path}.${key}`)
    })
  }
  if (Array.isArray(real) && Array.isArray(expected) && real.length > 0 && expected.length > 0) {
    return shapeDiff(real[0], expected[0], `${path}[]`)
  }
  return []
}
