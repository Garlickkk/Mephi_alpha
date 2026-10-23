import test from 'node:test';import assert from 'node:assert/strict';import {calculate} from '../dist/domain.js';
test('annuity reconciles principal and interest',()=>{const r=calculate(1500000,24);assert.ok(r.payment>62500);assert.ok(Math.abs(r.total-r.interest-1500000)<.001)});
test('longer term reduces payment and increases interest',()=>{const a=calculate(1500000,24),b=calculate(1500000,36);assert.ok(b.payment<a.payment);assert.ok(b.interest>a.interest)});
test('bounds reject invalid values',()=>{for(const v of [NaN,0,-1,10000001])assert.throws(()=>calculate(v,24));assert.throws(()=>calculate(100000,6.5))});
