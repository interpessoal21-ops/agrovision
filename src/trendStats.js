export function erf(x){const sign=x<0?-1:1;x=Math.abs(x);const t=1/(1+0.3275911*x);const y=1-(((((1.061405429*t-1.453152027)*t)+1.421413741)*t-0.284496736)*t+0.254829592)*t*Math.exp(-x*x);return sign*y;}
function normalP(z){return Math.max(0,Math.min(1,1-erf(Math.abs(z)/Math.SQRT2)));}
function validateAnnual(rows){
 const data=rows.map(r=>({year:Number(r.year??r.ano),value:Number(r.value??r.valor??r.anomaly??r.anomalia)})).filter(r=>Number.isInteger(r.year)&&Number.isFinite(r.value)).sort((a,b)=>a.year-b.year);
 if(data.length<8)throw new Error("São necessárias pelo menos 8 observações anuais válidas.");
 if(new Set(data.map(d=>d.year)).size!==data.length)throw new Error("Há anos duplicados. Cada ano deve aparecer uma única vez.");
 if(data.some((d,i)=>i&&d.year!==data[i-1].year+1))throw new Error("A série precisa ter anos consecutivos, sem lacunas, para a correção de autocorrelação.");
 return data;
}
export function rankValues(values){
 const order=values.map((v,i)=>({v,i})).sort((a,b)=>a.v-b.v),ranks=Array(values.length);let i=0;
 while(i<order.length){let j=i+1;while(j<order.length&&order[j].v===order[i].v)j++;const rank=(i+1+j)/2;for(let k=i;k<j;k++)ranks[order[k].i]=rank;i=j;}return ranks;
}
function median(values){const a=[...values].sort((x,y)=>x-y),m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;}
export function trendStats(input,{replicates=600,seed=42}={}){
 const data=validateAnnual(input),values=data.map(d=>d.value),n=values.length;let S=0;const slopes=[];
 for(let i=0;i<n;i++)for(let j=i+1;j<n;j++){S+=Math.sign(values[j]-values[i]);slopes.push((values[j]-values[i])/(data[j].year-data[i].year));}
 const slope=median(slopes);
 const counts=new Map();values.forEach(v=>counts.set(v,(counts.get(v)||0)+1));
 const tie=[...counts.values()].reduce((a,t)=>a+(t>1?t*(t-1)*(2*t+5):0),0);
 const variance=n*(n-1)*(2*n+5)/18-tie/18;
 let factor=1,adjustedLags=[];
 const detrended=values.map((v,i)=>v-(i+1)*slope),ranks=rankValues(detrended),mean=(n+1)/2,centered=ranks.map(v=>v-mean),denom=centered.reduce((a,v)=>a+v*v,0),rho=[];
 for(let lag=1;lag<n;lag++){let sum=0;for(let i=0;i<n-lag;i++)sum+=centered[i]*centered[i+lag];rho.push(denom?sum/denom:0);}
 const cutoff=1.96/Math.sqrt(n);let correctionSum=0;rho.forEach((r,i)=>{if(Math.abs(r)>cutoff){const lag=i+1;adjustedLags.push(lag);correctionSum+=(n-lag)*(n-lag-1)*(n-lag-2)*r;}});
 if(adjustedLags.length)factor=1+2*Math.abs(correctionSum)/(n*(n-1)*(n-2));
 const correctedVariance=variance*factor,z=correctedVariance<=0?0:(S===0?0:(S>0?S-1:S+1)/Math.sqrt(correctedVariance)),p=normalP(z);
 const x=data.map(d=>d.year-data[0].year),intercept=median(values.map((v,i)=>v-slope*x[i])),fitted=x.map(v=>intercept+slope*v),residual=values.map((v,i)=>v-fitted[i]);
 const blockLength=Math.max(2,Math.round(n**(1/3))),rng=(()=>{let a=seed>>>0;return()=>{a^=a<<13;a^=a>>>17;a^=a<<5;return(a>>>0)/4294967296;};})(),boot=[];
 for(let b=0;b<replicates;b++){const sampled=[];while(sampled.length<n){const st=Math.floor(rng()*n);for(let k=0;k<blockLength&&sampled.length<n;k++)sampled.push(residual[(st+k)%n]);}const slopesBoot=[];for(let i=0;i<n;i++)for(let j=i+1;j<n;j++)slopesBoot.push((fitted[j]+sampled[j]-fitted[i]-sampled[i])/(data[j].year-data[i].year));boot.push(median(slopesBoot));}
 boot.sort((a,b)=>a-b);const lo=boot[Math.floor(.025*(replicates-1))],hi=boot[Math.ceil(.975*(replicates-1))];
 return {data,n,S,tau:S/(n*(n-1)/2),slope,p,z,variance,correctedVariance,factor,adjustedLags,ci:{lower:lo,upper:hi,confidence:0.95,replicates,blockLength,seed},direction:slope>0?"Crescente":slope<0?"Decrescente":"Sem tendência monotônica",significant:p<.05};
}
