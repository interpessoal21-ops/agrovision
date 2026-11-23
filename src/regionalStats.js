import { trendStats, rankValues } from './trendStats.js';
export function benjaminiHochberg(items){
 if(items.some(item=>!Number.isFinite(item.p)||item.p<0||item.p>1))throw new Error('All p-values must be finite and between 0 and 1.');
 const sorted=items.map((x,i)=>({...x,_i:i})).sort((a,b)=>a.p-b.p),m=sorted.length;let next=1;
 for(let i=m-1;i>=0;i--){next=Math.min(next,sorted[i].p*m/(i+1),1);sorted[i].q=next;}
 return sorted.sort((a,b)=>a._i-b._i);
}
function haversineKm(a,b){
 const rad=Math.PI/180,dlat=(b.lat-a.lat)*rad,dlon=(b.lon-a.lon)*rad,h=Math.sin(dlat/2)**2+Math.cos(a.lat*rad)*Math.cos(b.lat*rad)*Math.sin(dlon/2)**2;
 return 6371*2*Math.asin(Math.sqrt(Math.max(0,Math.min(1,h))));
}
export function analyzeRegions(records,{replicates=600,seed=42}={}){
 const groups=new Map(),coords=new Map();
 for(const r of records){
  const region=String(r.region??r.regiao??'').trim(),rawYear=r.year??r.ano,rawValue=r.value??r.valor,year=rawYear===undefined||rawYear===null||String(rawYear).trim()===''?NaN:Number(rawYear),value=rawValue===undefined||rawValue===null||String(rawValue).trim()===''?NaN:Number(rawValue),rawLat=r.latitude??r.lat,rawLon=r.longitude??r.lon??r.lng,
   hasLat=rawLat!==undefined&&rawLat!==null&&String(rawLat).trim()!=='',hasLon=rawLon!==undefined&&rawLon!==null&&String(rawLon).trim()!=='',lat=hasLat?Number(rawLat):NaN,lon=hasLon?Number(rawLon):NaN;
  if(region){
   if(!Number.isInteger(year))throw new Error(`Ano inválido ou ausente na região ${region}.`);
   if(!Number.isFinite(value))throw new Error(`Valor ausente ou inválido na região ${region}, ano ${year}.`);
   if(!groups.has(region))groups.set(region,[]);groups.get(region).push({year,value});
   if(hasLat!==hasLon)throw new Error('Informe latitude e longitude juntas para cada região.');
   if(hasLat&&hasLon){
    if(!Number.isFinite(lat)||lat < -90||lat>90||lon < -180||lon>180)throw new Error('Coordenadas fora dos limites geográficos.');
    const previous=coords.get(region);if(previous&&(Math.abs(previous.lat-lat)>1e-6||Math.abs(previous.lon-lon)>1e-6))throw new Error('Cada região deve usar coordenadas consistentes em todas as observações.');
    if(!previous)coords.set(region,{lat,lon});
   }
  }
 }
 if(groups.size<2)throw new Error('A comparação espacial exige pelo menos duas regiões.');
 const regions=[...groups].map(([region,rows])=>({region,...trendStats(rows,{replicates,seed})}));
 const adjusted=benjaminiHochberg(regions.map(({region,p,n,slope,direction})=>({region,p,n,slope,direction})));
 adjusted.forEach((r,i)=>{regions[i].q=r.q;});
 let moran=null;const spatial=regions.filter(r=>coords.has(r.region));
 if(spatial.length>=4){
  const n=spatial.length,points=spatial.map(r=>({region:r.region,lat:coords.get(r.region).lat,lon:coords.get(r.region).lon,value:r.slope}));
  const weights=Array.from({length:n},()=>Array(n).fill(0)),k=Math.min(4,n-1);
  for(let i=0;i<n;i++){const near=points.map((p,j)=>({j,d:j===i?Infinity:haversineKm(points[i],p)})).sort((a,b)=>a.d-b.d).slice(0,k);for(const v of near)weights[i][v.j]=1;}
  for(let i=0;i<n;i++)for(let j=i+1;j<n;j++)if(weights[i][j]||weights[j][i])weights[i][j]=weights[j][i]=1;
  const mean=points.reduce((a,p)=>a+p.value,0)/n,dev=points.map(p=>p.value-mean),den=dev.reduce((a,v)=>a+v*v,0);let num=0,s0=0;
  for(let i=0;i<n;i++)for(let j=0;j<n;j++){num+=weights[i][j]*dev[i]*dev[j];s0+=weights[i][j];}
  if(den>0&&s0>0)moran={I:(n/s0)*(num/den),n,k,regions:points};
 }
 return {regions,moran};
}
function pearson(a,b){
 const ma=a.reduce((x,v)=>x+v,0)/a.length,mb=b.reduce((x,v)=>x+v,0)/b.length;let num=0,da=0,db=0;
 for(let i=0;i<a.length;i++){const x=a[i]-ma,y=b[i]-mb;num+=x*y;da+=x*x;db+=y*y;}return da&&db?num/Math.sqrt(da*db):NaN;
}
export function correlateVariables(records){
 const byRegion=new Map();
 for(const r of records){
  const region=String(r.region??r.regiao??'').trim(),rawYear=r.year??r.ano,rawValue=r.value??r.valor,year=rawYear===undefined||rawYear===null||String(rawYear).trim()===''?NaN:Number(rawYear),variable=String(r.variable??r.variavel??'').trim(),value=rawValue===undefined||rawValue===null||String(rawValue).trim()===''?NaN:Number(rawValue);
  if(region&&Number.isInteger(year)&&variable&&Number.isFinite(value)){
   if(!byRegion.has(region))byRegion.set(region,new Map());const vars=byRegion.get(region);
   if(!vars.has(variable))vars.set(variable,new Map());const series=vars.get(variable);
   if(series.has(year))throw new Error(`Duplicate observation for ${region}, ${year}, ${variable}.`);
   series.set(year,value);
  }
 }
 const out=[];
 for(const [region,vars] of byRegion){const names=[...vars.keys()];
  for(let i=0;i<names.length;i++)for(let j=i+1;j<names.length;j++){
   const aName=names[i],bName=names[j],aSeries=vars.get(aName),bSeries=vars.get(bName),years=[...aSeries.keys()].filter(y=>bSeries.has(y)).sort((x,y)=>x-y);
   if(years.length>=8){const a=years.map(y=>aSeries.get(y)),b=years.map(y=>bSeries.get(y));out.push({region,a:aName,b:bName,n:years.length,pearson:pearson(a,b),spearman:pearson(rankValues(a),rankValues(b))});}
  }
 }
 if(!out.length)throw new Error('Nenhum par de variáveis tem pelo menos 8 anos coincidentes na mesma região.');
 return out;
}
