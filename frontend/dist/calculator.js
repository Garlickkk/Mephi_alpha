export function catalogBounds(products) {
  if (!products.length) return null;
  return {
    min: Math.min(...products.map(p => p.min)),
    max: Math.max(...products.map(p => p.max)),
    minMonths: Math.min(...products.map(p => p.minMonths)),
    maxMonths: Math.max(...products.map(p => p.maxMonths)),
  };
}

export function fitsProduct(product, amount, months) {
  return amount >= product.min && amount <= product.max &&
    months >= product.minMonths && months <= product.maxMonths && months % 12 === 0;
}

export function fitTerms(bounds, amount, months) {
  return {
    amount: Math.min(bounds.max, Math.max(bounds.min, amount)),
    months: Math.min(bounds.maxMonths, Math.max(bounds.minMonths, Math.round(months / 12) * 12)),
  };
}
