import test from 'node:test';
import assert from 'node:assert/strict';
import {catalogBounds, fitTerms, fitsProduct} from '../dist/calculator.js';
import {normalizeProduct} from '../dist/api.js';

const product = normalizeProduct({
  minSum: 50000, maxSum: 3000000, minDurationYear: 1, maxDurationYear: 5,
});

test('slider limits come from the catalog, with backend years converted to months', () => {
  assert.deepEqual(catalogBounds([product]), {
    min: 50000, max: 3000000, minMonths: 12, maxMonths: 60,
  });
  assert.equal(catalogBounds([]), null);
});

test('a 30-year selection is adjusted to an available term and can be submitted', () => {
  const terms = fitTerms(product, 1000000, 360);
  assert.deepEqual(terms, {amount: 1000000, months: 60});
  assert.equal(fitsProduct(product, terms.amount, terms.months), true);
});

test('both amount and term fit exact product limits, including non-round sums', () => {
  const unusual = {...product, min: 75001, max: 2999999};
  assert.deepEqual(fitTerms(unusual, 50000, 6), {amount: 75001, months: 12});
  assert.deepEqual(fitTerms(unusual, 30000000, 360), {amount: 2999999, months: 60});
  assert.equal(fitsProduct(unusual, 75001, 12), true);
  assert.equal(fitsProduct(unusual, 2999999, 60), true);
  assert.equal(fitsProduct(unusual, 75000, 12), false);
  assert.equal(fitsProduct(unusual, 2999999, 72), false);
  assert.equal(fitsProduct(unusual, 1000000, 18), false);
});

test('valid selections are preserved and gaps between products remain ineligible', () => {
  assert.deepEqual(fitTerms(product, 1000000, 24), {amount: 1000000, months: 24});
  const other = {...product, min: 5000000, max: 10000000, minMonths: 72, maxMonths: 120};
  assert.equal(catalogBounds([product, other]).maxMonths, 120);
  assert.equal(fitsProduct(product, 4000000, 60), false);
  assert.equal(fitsProduct(other, 4000000, 60), false);
  assert.deepEqual(fitTerms(other, 4000000, 60), {amount: 5000000, months: 72});
});
