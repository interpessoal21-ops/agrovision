import test from 'node:test';
import assert from 'node:assert/strict';
import { trendStats, rankValues } from '../src/trendStats.js';
const rows=(values,start=2000)=>values.map((value,i)=>({year:start+i,value}));
test('web trend analysis computes Sen slope and a finite Hamed–Rao result',()=>{
 const r=trendStats(rows(Array.from({length:12},(_,i)=>2+.25*i)),{replicates:250,seed:7});
 assert.equal(r.slope,.25);assert.equal(r.direction,'Crescente');assert.ok(Number.isFinite(r.p));assert.ok(r.p>=0&&r.p<=1);assert.ok(r.factor>=1);assert.equal(r.ci.lower,.25);assert.equal(r.ci.upper,.25);
});
test('average ranks are used for ties',()=>assert.deepEqual(rankValues([4,4,8,10,10]),[1.5,1.5,3,4.5,4.5]));
test('rejects duplicate years and gaps in annual series',()=>{
 assert.throws(()=>trendStats([{year:2000,value:1},{year:2000,value:2},...rows([3,4,5,6,7,8],2001)]),/duplicados/);
 assert.throws(()=>trendStats(rows([1,2,3,4,5,6,7,8,9],2000).filter((_,i)=>i!==3)),/consecutivos/);
});
test('bootstrap interval is reproducible for fixed seed',()=>{
 const noisy=rows([1,2,1,3,4,3,5,4,7,6,8,7,9,10,8,12,11,13,12,14]);
 const a=trendStats(noisy,{replicates:250,seed:19}),b=trendStats(noisy,{replicates:250,seed:19});
 assert.deepEqual(a.ci,b.ci);
});

test('blank annual values are rejected instead of converted to zero',()=>{
 const incomplete=rows([1,2,3,4,5,6,7,8]);incomplete[4].value='';
 assert.throws(()=>trendStats(incomplete),/Valor anual ausente ou inválido/);
});
