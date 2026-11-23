import test from 'node:test';
import assert from 'node:assert/strict';
import { benjaminiHochberg, analyzeRegions, correlateVariables } from '../src/regionalStats.js';
test('Benjamini–Hochberg matches canonical adjusted p-values',()=>{
 const result=benjaminiHochberg([{id:'a',p:.01},{id:'b',p:.04},{id:'c',p:.03},{id:'d',p:.2}]);
 assert.deepEqual(result.map(x=>x.q),[.04,.05333333333333334,.05333333333333334,.2]);
});
test('Moran I matches the complete-graph analytical reference',()=>{
 const slopes=[1,2,-1,-2],coords=[[0,0],[0,1],[1,0],[1,1]],records=[];
 for(let r=0;r<4;r++)for(let y=0;y<8;y++)records.push({region:`R${r}`,year:2000+y,value:slopes[r]*y,latitude:coords[r][0],longitude:coords[r][1]});
 const result=analyzeRegions(records,{replicates:250,seed:2});
 assert.equal(result.moran.n,4);assert.equal(result.moran.k,3);assert.ok(Math.abs(result.moran.I+1/3)<1e-12);
 assert.equal(result.regions.length,4);assert.ok(result.regions.every(r=>Number.isFinite(r.q)&&r.q>=0&&r.q<=1));
});
test('Moran is not calculated when fewer than four regions have coordinates',()=>{
 const records=[];for(let r=0;r<4;r++)for(let y=0;y<8;y++)records.push({region:`R${r}`,year:2000+y,value:y, ...(r<3?{latitude:r,longitude:r+1}:{})});
 assert.equal(analyzeRegions(records,{replicates:200}).moran,null);
});
test('Pearson and Spearman use sorted common years only',()=>{
 const records=[];for(let y=2000;y<2010;y++)records.push({region:'R',year:y,variable:'x',value:y-1999});
 for(let y=2002;y<2010;y++)records.push({region:'R',year:y,variable:'y',value:3+2*(y-1999)});
 const [r]=correlateVariables(records);assert.equal(r.n,8);assert.equal(r.pearson,1);assert.equal(r.spearman,1);
});
test('rejects duplicate regional-variable-year rows rather than silently overwriting',()=>{
 const records=[];for(let y=2000;y<2008;y++){records.push({region:'R',year:y,variable:'x',value:y},{region:'R',year:y,variable:'y',value:2*y});}
 records.push({region:'R',year:2000,variable:'x',value:999});assert.throws(()=>correlateVariables(records),/Duplicate observation/);
});

test('blank values are omitted from paired correlations, not treated as zero',()=>{
 const records=[];for(let y=2000;y<2009;y++)records.push({region:'R',year:y,variable:'x',value:y-1999});
 for(let y=2000;y<2009;y++)records.push({region:'R',year:y,variable:'y',value:y===2001?'':3+2*(y-1999)});
 const [r]=correlateVariables(records);assert.equal(r.n,8);assert.equal(r.pearson,1);assert.equal(r.spearman,1);
});
test('regional trend CSV rejects blank numeric values instead of zero filling',()=>{
 const records=[];for(let y=2000;y<2008;y++)for(let r=0;r<2;r++)records.push({region:`R${r}`,year:y,value:r===0&&y===2003?'':y,latitude:r,longitude:r+1});
 assert.throws(()=>analyzeRegions(records,{replicates:200}),/Valor ausente ou inválido/);
});
