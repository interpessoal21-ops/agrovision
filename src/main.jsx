import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, ArrowUpRight, Globe2, Layers3, Menu, Satellite, Sprout, Wind, Flame, ExternalLink, Compass, Database, FlaskConical, Languages, CircleHelp, Upload, RefreshCw } from "lucide-react";
import "./style.css";
import "./brand.css";

const copy = {
  en: {
    eyebrow:"TERRITORY · CLIMATE · FUTURE", title:"From the fields to the sea,\nwith Brazil on the horizon.",
    intro:"GUMA connects climate intelligence, Earth observation and agricultural systems through a global, evidence-led view of the planet.",
    explore:"Open Trend Detective", docs:"Project methodology", overview:"Overview", climate:"Trend Detective", observatory:"Earth observatory", agriculture:"Agro-systems", methods:"Methods & sources",
    global:"GLOBAL COVERAGE", status:"WEB EDITION · RESEARCH PREVIEW", signal:"A changing planet, in context", signalText:"Independent Earth data streams, with source, time range and interpretation limits visible.",
    temp:"Global temperature", co2:"Atmospheric CO₂", fire:"Active fire observations", satellite:"Satellite scene discovery",
    source:"DATA SOURCES", focus:"Built for evidence, not black boxes", focusText:"Every layer keeps its lineage visible. Screening outputs are not forecasts and correlation is not causation.",
    nasa:"NASA GISS · GISTEMP", power:"NASA POWER", firms:"NASA FIRMS", sentinel:"Sentinel-2 · Earth Search",
    note:"Research prototype", noteText:"The web edition is being expanded in stages. Analytical results show their source, method and limitations.",
    legacy:"Open Streamlit research prototype", footer:"From the fields to the sea, with Brazil on the horizon. · Independent research prototype; not affiliated with NASA."
  },
  pt: {
    eyebrow:"TERRITÓRIO · CLIMA · FUTURO", title:"Do campo ao mar,\ncom o Brasil no horizonte.",
    intro:"O GUMA conecta inteligência climática, observação da Terra e sistemas agrícolas em uma leitura global do planeta, orientada por evidências.",
    explore:"Abrir Trend Detective", docs:"Metodologia do projeto", overview:"Visão geral", climate:"Trend Detective", observatory:"Observatório da Terra", agriculture:"Sistemas agrícolas", methods:"Métodos e fontes",
    global:"COBERTURA GLOBAL", status:"EDIÇÃO WEB · PRÉVIA DE PESQUISA", signal:"Um planeta em transformação, em contexto", signalText:"Fluxos independentes de dados da Terra, com fontes, períodos e limites de interpretação visíveis.",
    temp:"Temperatura global", co2:"CO₂ atmosférico", fire:"Observações de focos de fogo", satellite:"Descoberta de cenas orbitais",
    source:"FONTES DE DADOS", focus:"Feito para evidências, não para caixas-pretas", focusText:"Cada camada mantém sua origem visível. Triagens não são previsões e correlação não significa causalidade.",
    nasa:"NASA GISS · GISTEMP", power:"NASA POWER", firms:"NASA FIRMS", sentinel:"Sentinel-2 · Earth Search",
    note:"Protótipo de pesquisa", noteText:"A edição web está sendo ampliada por etapas. Os resultados analíticos informam suas fontes, métodos e limitações.",
    legacy:"Abrir protótipo Streamlit", footer:"Do campo ao mar, com o Brasil no horizonte. · Protótipo independente; sem vínculo com a NASA."
  }
};
const nav=[["overview",Globe2],["climate",Activity],["observatory",Satellite],["agriculture",Sprout],["methods",FlaskConical]];

function erf(x){const sign=x<0?-1:1;x=Math.abs(x);const t=1/(1+0.3275911*x);const y=1-(((((1.061405429*t-1.453152027)*t)+1.421413741)*t-0.284496736)*t+0.254829592)*t*Math.exp(-x*x);return sign*y;}
function analyze(rows){
 const data=rows.filter(d=>Number.isFinite(d.year)&&Number.isFinite(d.value)).sort((a,b)=>a.year-b.year);
 if(data.length<8)throw new Error("São necessárias pelo menos oito observações anuais válidas.");
 if(new Set(data.map(d=>d.year)).size!==data.length)throw new Error("Há anos duplicados. Cada ano deve aparecer uma única vez.");
 let S=0, slopes=[];
 for(let i=0;i<data.length;i++)for(let j=i+1;j<data.length;j++){S+=Math.sign(data[j].value-data[i].value);slopes.push((data[j].value-data[i].value)/(data[j].year-data[i].year));}
 const counts=new Map();data.forEach(d=>counts.set(d.value,(counts.get(d.value)||0)+1));
 const n=data.length, tie=[...counts.values()].reduce((a,t)=>a+(t>1?t*(t-1)*(2*t+5):0),0);
 const variance=(n*(n-1)*(2*n+5)-tie)/18;
 const z=variance<=0?0:(S>0?(S-1)/Math.sqrt(variance):S<0?(S+1)/Math.sqrt(variance):0);
 const p=1-erf(Math.abs(z)/Math.SQRT2);slopes.sort((a,b)=>a-b);
 const slope=slopes.length%2?slopes[(slopes.length-1)/2]:(slopes[slopes.length/2-1]+slopes[slopes.length/2])/2;
 return {data,n,tau:S/(n*(n-1)/2),slope,p,direction:slope>0?"Crescente":slope<0?"Decrescente":"Sem tendência monotônica",significant:p<0.05};
}
function parseCSV(text){
 const lines=text.replace(/^\uFEFF/,"").trim().split(/\r?\n/);if(lines.length<2)throw new Error("CSV vazio ou sem linhas de dados.");
 const split=line=>{const out=[];let value="",quoted=false;for(let i=0;i<line.length;i++){const c=line[i];if(c==='"'&&line[i+1]==='"'&&quoted){value+='"';i++;}else if(c==='"')quoted=!quoted;else if(c===","&&!quoted){out.push(value.trim());value="";}else value+=c;}out.push(value.trim());return out;};
 const headers=split(lines.shift()).map(x=>x.replace(/^"|"$/g,"").trim().toLowerCase());
 return lines.filter(x=>x.trim()).map(line=>{const cells=split(line);return Object.fromEntries(headers.map((h,i)=>[h,(cells[i]||"").replace(/^"|"$/g,"").trim()]));});
}
function normalP(z){return Math.max(0,Math.min(1,1-erf(Math.abs(z)/Math.SQRT2)));}
function validateAnnual(rows){
 const data=rows.map(r=>({year:Number(r.year??r.ano),value:Number(r.value??r.valor??r.anomaly??r.anomalia)})).filter(r=>Number.isInteger(r.year)&&Number.isFinite(r.value)).sort((a,b)=>a.year-b.year);
 if(data.length<8)throw new Error("São necessárias pelo menos 8 observações anuais válidas.");
 if(new Set(data.map(d=>d.year)).size!==data.length)throw new Error("Há anos duplicados na série.");
 if(data.some((d,i)=>i&&d.year!==data[i-1].year+1))throw new Error("A série precisa ter anos consecutivos, sem lacunas, para a correção de autocorrelação.");
 return data;
}
function rankValues(values){
 const order=values.map((v,i)=>({v,i})).sort((a,b)=>a.v-b.v),ranks=Array(values.length);let i=0;
 while(i<order.length){let j=i+1;while(j<order.length&&order[j].v===order[i].v)j++;const rank=(i+1+j)/2;for(let k=i;k<j;k++)ranks[order[k].i]=rank;i=j;}return ranks;
}
function median(values){const a=[...values].sort((x,y)=>x-y),m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;}
function trendStats(input,{replicates=600,seed=42}={}){
 const data=validateAnnual(input),values=data.map(d=>d.value),n=values.length;let S=0;const slopes=[];
 for(let i=0;i<n;i++)for(let j=i+1;j<n;j++){S+=Math.sign(values[j]-values[i]);slopes.push((values[j]-values[i])/(data[j].year-data[i].year));}
 const counts=new Map();values.forEach(v=>counts.set(v,(counts.get(v)||0)+1));
 const tie=[...counts.values()].reduce((a,t)=>a+(t>1?t*(t-1)*(2*t+5):0),0);
 const variance=n*(n-1)*(2*n+5)/18-tie/18;
 const rawZ=variance<=0||S===0?0:(S>0?S-1:S+1)/Math.sqrt(variance);
 let factor=1,adjustedLags=[];
 const detrended=values.map((v,i)=>v-(i+1)*slope),ranks=rankValues(detrended),mean=(n+1)/2,centered=ranks.map(v=>v-mean),denom=centered.reduce((a,v)=>a+v*v,0),rho=[];
 for(let lag=1;lag<n;lag++){let sum=0;for(let i=0;i<n-lag;i++)sum+=centered[i]*centered[i+lag];rho.push(denom?sum/denom:0);}
 const cutoff=1.96/Math.sqrt(n);let correctionSum=0;rho.forEach((r,i)=>{if(Math.abs(r)>cutoff){const lag=i+1;adjustedLags.push(lag);correctionSum+=(n-lag)*(n-lag-1)*(n-lag-2)*r;}});
 if(adjustedLags.length)factor=1+2*Math.abs(correctionSum)/(n*(n-1)*(n-2));
 const correctedVariance=variance*factor,z=correctedVariance<=0?0:(S===0?0:(S>0?S-1:S+1)/Math.sqrt(correctedVariance)),p=normalP(z),slope=median(slopes);
 const x=data.map(d=>d.year-data[0].year),intercept=median(values.map((v,i)=>v-slope*x[i])),fitted=x.map(v=>intercept+slope*v),residual=values.map((v,i)=>v-fitted[i]);
 const blockLength=Math.max(2,Math.round(n**(1/3))),rng=(()=>{let a=seed>>>0;return()=>{a^=a<<13;a^=a>>>17;a^=a<<5;return(a>>>0)/4294967296;};})(),boot=[];
 for(let b=0;b<replicates;b++){const sampled=[];while(sampled.length<n){const st=Math.floor(rng()*n);for(let k=0;k<blockLength&&sampled.length<n;k++)sampled.push(residual[(st+k)%n]);}const slopesBoot=[];for(let i=0;i<n;i++)for(let j=i+1;j<n;j++)slopesBoot.push((fitted[j]+sampled[j]-fitted[i]-sampled[i])/(data[j].year-data[i].year));boot.push(median(slopesBoot));}
 boot.sort((a,b)=>a-b);const lo=boot[Math.floor(.025*(replicates-1))],hi=boot[Math.ceil(.975*(replicates-1))];
 return {data,n,S,tau:S/(n*(n-1)/2),slope,p,z,variance,correctedVariance,factor,adjustedLags,ci:{lower:lo,upper:hi,confidence:0.95,replicates,blockLength,seed},direction:slope>0?"Crescente":slope<0?"Decrescente":"Sem tendência monotônica",significant:p<.05};
}
function benjaminiHochberg(items){
 const sorted=items.map((x,i)=>({...x,_i:i})).sort((a,b)=>a.p-b.p),m=sorted.length;let next=1;
 for(let i=m-1;i>=0;i--){next=Math.min(next,sorted[i].p*m/(i+1),1);sorted[i].q=next;}
 return sorted.sort((a,b)=>a._i-b._i);
}
function analyzeRegions(records){
 const groups=new Map();for(const r of records){const region=String(r.region??r.regiao??"").trim(),year=Number(r.year??r.ano),value=Number(r.value??r.valor);if(region&&Number.isInteger(year)&&Number.isFinite(value)){if(!groups.has(region))groups.set(region,[]);groups.get(region).push({year,value});}}
 if(groups.size<2)throw new Error("A comparação espacial exige pelo menos duas regiões.");
 const results=[...groups].map(([region,rows])=>({region,...trendStats(rows)}));
 return benjaminiHochberg(results.map(({region,p,n,slope,direction})=>({region,p,n,slope,direction}))).map((r,i)=>({...results[i],q:r.q}));
}
function pearson(a,b){
 const ma=a.reduce((x,v)=>x+v,0)/a.length,mb=b.reduce((x,v)=>x+v,0)/b.length;let num=0,da=0,db=0;
 for(let i=0;i<a.length;i++){const x=a[i]-ma,y=b[i]-mb;num+=x*y;da+=x*x;db+=y*y;}return da&&db?num/Math.sqrt(da*db):NaN;
}
function correlateVariables(records){
 const map=new Map();for(const r of records){const region=String(r.region??r.regiao??"").trim(),year=Number(r.year??r.ano),variable=String(r.variable??r.variavel??"").trim(),value=Number(r.value??r.valor);if(region&&Number.isInteger(year)&&variable&&Number.isFinite(value))map.set([region,year,variable].join("|"),value);}
 const regions=[...new Set([...map.keys()].map(k=>k.split("|")[0]))],out=[];
 for(const region of regions){const vars=[...new Set([...map.keys()].filter(k=>k.startsWith(region+"|")).map(k=>k.split("|")[2]))];
  for(let i=0;i<vars.length;i++)for(let j=i+1;j<vars.length;j++){const a=[],b=[];for(const key of map.keys()){const [reg,year,v]=key.split("|");if(reg===region&&v===vars[i]&&map.has([region,year,vars[j]].join("|"))){a.push(map.get(key));b.push(map.get([region,year,vars[j]].join("|")));}}
   if(a.length>=8){const rp=pearson(a,b),rs=pearson(rankValues(a),rankValues(b));out.push({region,a:vars[i],b:vars[j],n:a.length,pearson:rp,spearman:rs});}
  }
 }
 if(!out.length)throw new Error("Nenhum par de variáveis tem pelo menos 8 anos coincidentes na mesma região.");
 return out;
}
function TrendDetective({lang}){
 const [rows,setRows]=useState([]),[source,setSource]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState(""),[result,setResult]=useState(null);
 const [regionRows,setRegionRows]=useState([]),[regionResults,setRegionResults]=useState([]),[regionError,setRegionError]=useState("");
 const [variableRows,setVariableRows]=useState([]),[correlations,setCorrelations]=useState([]),[variableError,setVariableError]=useState("");
 const [start,setStart]=useState(""),[end,setEnd]=useState("");const t=lang==="pt";
 const selected=useMemo(()=>rows.filter(r=>(!start||r.year>=Number(start))&&(!end||r.year<=Number(end))),[rows,start,end]);
 const loadNASA=async()=>{setBusy(true);setError("");setResult(null);try{const r=await fetch("/api/gistemp");const j=await r.json();if(!r.ok)throw new Error(j.error||"Falha ao consultar NASA GISTEMP.");setRows(j.rows);setSource("NASA GISS · GISTEMP v4");setStart(String(j.rows[0].year));setEnd(String(j.rows[j.rows.length-1].year));}catch(e){setError(e.message+" Você ainda pode importar uma série anual em CSV.");}finally{setBusy(false);}};
 const upload=async file=>{setError("");setResult(null);try{const parsed=parseCSV(await file.text()).map(r=>({year:Number(r.year??r.ano),value:Number(r.value??r.valor??r.anomaly??r.anomalia)})).filter(r=>Number.isFinite(r.year)&&Number.isFinite(r.value)).sort((a,b)=>a.year-b.year);validateAnnual(parsed);setRows(parsed);setSource("Arquivo enviado · "+file.name);setStart(String(parsed[0].year));setEnd(String(parsed[parsed.length-1].year));}catch(e){setError(e.message);}};
 const run=()=>{try{setResult(trendStats(selected));setError("");}catch(e){setResult(null);setError(e.message);}};
 const uploadRegions=async file=>{try{const parsed=parseCSV(await file.text());setRegionRows(parsed);setRegionResults(analyzeRegions(parsed));setRegionError("");}catch(e){setRegionResults([]);setRegionError(e.message);}};
 const uploadVariables=async file=>{try{const parsed=parseCSV(await file.text());setVariableRows(parsed);setCorrelations(correlateVariables(parsed));setVariableError("");}catch(e){setCorrelations([]);setVariableError(e.message);}};
 return <section className="trend-workspace">
  <div className="eyebrow">GUMA / EARTH SYSTEM TREND DETECTIVE</div><h1>{t?"Investigue tendências ambientais.":"Investigate Earth-system trends."}</h1>
  <p className="trend-lead">{t?"Mann–Kendall com ajuste Hamed–Rao, inclinação de Sen e IC bootstrap. Compare regiões e explore relações entre variáveis ambientais.":"Mann–Kendall with Hamed–Rao adjustment, Sen's slope and bootstrap CI. Compare regions and explore relationships between environmental variables."}</p>
  <div className="trend-controls"><button className="primary" onClick={loadNASA} disabled={busy}><RefreshCw size={16}/>{busy?"Consultando NASA…":(t?"Carregar NASA GISTEMP":"Load NASA GISTEMP")}</button><label className="upload-control"><Upload size={16}/>{t?"Enviar série anual CSV":"Upload annual-series CSV"}<input type="file" accept=".csv,text/csv" onChange={e=>e.target.files?.[0]&&upload(e.target.files[0])}/></label></div>
  {source&&<div className="dataset-meta"><Database size={15}/><span><b>Fonte:</b> {source} · {rows.length} observações · {rows[0]?.year}–{rows[rows.length-1]?.year}</span></div>}
  {rows.length>0&&<div className="analysis-panel"><h2>{t?"Análise temporal":"Time-series analysis"}</h2><div className="year-controls"><label>Ano inicial<input type="number" value={start} onChange={e=>setStart(e.target.value)}/></label><label>Ano final<input type="number" value={end} onChange={e=>setEnd(e.target.value)}/></label><button className="primary" onClick={run}>{t?"Analisar tendência":"Analyze trend"}</button></div><p className="subtle">{selected.length} observações selecionadas · mínimo 8 anos consecutivos</p></div>}
  {error&&<div className="error-panel" role="alert">{error}</div>}
  {result&&<div className="results-panel"><div className="result-heading"><div><div className="eyebrow">RESULTADO ESTATÍSTICO</div><h2>{result.direction}</h2></div><span className={result.significant?"significance yes":"significance"}>{result.significant?"Significativo · p ajustado por Hamed–Rao":"Não significativo · p ajustado por Hamed–Rao"}</span></div>
   <div className="result-metrics"><article><small>Sen's slope</small><b>{result.slope.toFixed(4)}</b><span>unidades / ano</span></article><article><small>IC 95% da inclinação</small><b>{result.ci.lower.toFixed(4)} a {result.ci.upper.toFixed(4)}</b><span>bootstrap em blocos · {result.ci.replicates} réplicas</span></article><article><small>Mann–Kendall τ</small><b>{result.tau.toFixed(3)}</b><span>p = {result.p.toPrecision(4)}</span></article><article><small>Autocorrelação</small><b>{result.factor.toFixed(3)}×</b><span>Hamed–Rao · {result.adjustedLags.length} defasagens</span></article></div>
   <div className="chart-panel"><h3>Série anual observada</h3><svg viewBox="0 0 760 260" role="img" aria-label="Série anual"><line x1="44" y1="12" x2="44" y2="220" stroke="currentColor" opacity=".35"/><line x1="44" y1="220" x2="740" y2="220" stroke="currentColor" opacity=".35"/><polyline fill="none" stroke="#17647a" strokeWidth="3" points={result.data.map((d,i)=>{const min=Math.min(...result.data.map(x=>x.value)),max=Math.max(...result.data.map(x=>x.value)),x=44+i*696/Math.max(1,result.n-1),y=204-(d.value-min)/(max-min||1)*180;return x.toFixed(1)+","+y.toFixed(1)}).join(" ")}/><text x="44" y="245" fill="currentColor" fontSize="12">{result.data[0].year}</text><text x="740" y="245" textAnchor="end" fill="currentColor" fontSize="12">{result.data[result.n-1].year}</text></svg></div>
   <details className="method-details"><summary>Método, parâmetros e limites</summary><p>Mann–Kendall com variância corrigida por Hamed–Rao usando autocorrelação dos postos; limiar normal 1,96/√n. A inclinação de Sen é a mediana das inclinações pareadas.</p><p>IC de 95%: bootstrap circular de blocos móveis dos resíduos após remoção da tendência, {result.ci.replicates} réplicas, comprimento do bloco {result.ci.blockLength}, semente {result.ci.seed}. A cobertura depende da estrutura temporal e do tamanho amostral; não é garantia universal.</p><p>O Hamed–Rao implementado é uma aproximação com seleção de defasagens pelo limiar nominal; séries curtas, tendência residual, mudanças estruturais e dados não estacionários exigem análise adicional. Resultado não implica causalidade.</p></details>
  </div>}
  <div className="analysis-panel"><h2>{t?"Comparação entre regiões":"Cross-region comparison"}</h2><p className="subtle">{t?"CSV longo: region, year, value. Cada região precisa ter pelo menos 8 anos consecutivos.":"Long CSV: region, year, value. Each region needs at least 8 consecutive years."}</p><label className="upload-control"><Upload size={16}/>Enviar CSV de regiões<input type="file" accept=".csv,text/csv" onChange={e=>e.target.files?.[0]&&uploadRegions(e.target.files[0])}/></label>{regionError&&<div className="error-panel">{regionError}</div>}{regionResults.length>0&&<div className="table-scroll"><table className="comparison-table"><thead><tr><th>Região</th><th>n</th><th>Sen / ano</th><th>p HR</th><th>q BH</th><th>Direção</th></tr></thead><tbody>{regionResults.map(r=><tr key={r.region}><td>{r.region}</td><td>{r.n}</td><td>{r.slope.toFixed(4)}</td><td>{r.p.toPrecision(3)}</td><td>{r.q.toPrecision(3)}</td><td>{r.direction}</td></tr>)}</tbody></table><p className="subtle">q: correção Benjamini–Hochberg para controlar taxa de falsas descobertas entre as regiões carregadas. A tabela compara regiões; não substitui análise geoespacial com coordenadas ou polígonos.</p></div>}</div>
  <div className="analysis-panel"><h2>{t?"Cruzamento de variáveis ambientais":"Environmental-variable relationships"}</h2><p className="subtle">{t?"CSV longo: region, year, variable, value. Ex.: temperatura, precipitação, umidade, NDVI. Serão usados somente anos coincidentes.":"Long CSV: region, year, variable, value. E.g. temperature, precipitation, humidity, NDVI. Only overlapping years are used."}</p><label className="upload-control"><Upload size={16}/>Enviar CSV multivariável<input type="file" accept=".csv,text/csv" onChange={e=>e.target.files?.[0]&&uploadVariables(e.target.files[0])}/></label>{variableError&&<div className="error-panel">{variableError}</div>}{correlations.length>0&&<div className="table-scroll"><table className="comparison-table"><thead><tr><th>Região</th><th>Variáveis</th><th>n pareado</th><th>Pearson r</th><th>Spearman ρ</th></tr></thead><tbody>{correlations.map((r,i)=><tr key={i}><td>{r.region}</td><td>{r.a} × {r.b}</td><td>{r.n}</td><td>{Number.isFinite(r.pearson)?r.pearson.toFixed(3):"—"}</td><td>{Number.isFinite(r.spearman)?r.spearman.toFixed(3):"—"}</td></tr>)}</tbody></table><p className="subtle">Correlação não demonstra causalidade. São exibidas estatísticas descritivas sem inferência causal nem correção de confundidores.</p></div>}</div>
  <div className="scope-note"><CircleHelp size={16}/><span>Use dados com fonte, unidade, método de medição e cobertura temporal documentados. A comparação regional não cria mapas nem pressupõe coordenadas que não estejam no arquivo.</span></div>
 </section>;
}
function App(){
 const [lang,setLang]=useState("pt"),[section,setSection]=useState("overview"),[mobileOpen,setMobileOpen]=useState(false);const t=copy[lang];
 const sectionTitle=t[section]||t.overview;
 return <div className="shell"><aside className={mobileOpen?"sidebar open":"sidebar"}>
  <a className="brand" href="#" onClick={()=>setSection("overview")}><span className="brand-mark"><img src="/guma-mark.svg" alt=""/></span><span><strong>GUMA</strong><small>TERRITÓRIO · CLIMA · FUTURO</small></span></a>
  <div className="side-label">WORKSPACE</div><nav>{nav.map(([key,Icon])=><button key={key} className={section===key?"nav-item active":"nav-item"} onClick={()=>{setSection(key);setMobileOpen(false);}}><Icon size={17}/><span>{t[key]}</span></button>)}</nav>
  <div className="side-bottom"><div className="global-pill"><Globe2 size={15}/><span>{t.global}</span></div><p>Earth data · Climate · Agriculture</p><a href="https://github.com/interpessoal21-ops/agrovision" target="_blank" rel="noreferrer">GitHub repository <ExternalLink size={12}/></a></div>
 </aside><main className="main"><header className="topbar"><button className="mobile-menu" onClick={()=>setMobileOpen(!mobileOpen)} aria-label="Toggle navigation"><Menu/></button><div className="crumb"><span>GUMA</span><i>/</i>{sectionTitle}</div><div className="top-actions"><span className="status"><span/> {t.status}</span><button className="lang" onClick={()=>setLang(lang==="en"?"pt":"en")}><Languages size={15}/>{lang.toUpperCase()}</button></div></header>
 {section==="climate"?<TrendDetective lang={lang}/>:section==="overview"?<>
  <section className="hero"><div className="hero-grid"/><div className="hero-copy"><div className="eyebrow"><span/>{t.eyebrow}</div><h1>{t.title.split("\n").map((line,i)=><React.Fragment key={i}>{i>0&&<br/>}{line}</React.Fragment>)}</h1><p>{t.intro}</p><div className="hero-actions"><button className="primary" onClick={()=>setSection("climate")}>{t.explore}<ArrowUpRight size={16}/></button><button className="secondary" onClick={()=>setSection("methods")}>{t.docs}<ExternalLink size={14}/></button></div></div><div className="hero-art" aria-hidden="true"><img className="carybe-scene" src="/guma-carybe-scene.svg" alt=""/></div><div className="hero-index"><span>01</span><span> / </span><span>05</span></div></section>
  <section className="metrics"><div className="metric-head"><span>01 / {t.signal}</span><span>GLOBAL SYSTEMS</span></div><div className="metric-grid"><article className="metric-card"><div className="metric-icon"><Activity size={18}/></div><span className="metric-label">{t.temp}</span><strong>GISTEMP v4</strong><small>1880 — present · Monthly & annual</small></article><article className="metric-card"><div className="metric-icon"><Wind size={18}/></div><span className="metric-label">{t.co2}</span><strong>Mauna Loa · CO₂</strong><small>Monthly station observations · ppm</small></article><article className="metric-card"><div className="metric-icon"><Flame size={18}/></div><span className="metric-label">{t.fire}</span><strong>VIIRS · FIRMS</strong><small>Rolling observations · Global</small></article><article className="metric-card"><div className="metric-icon"><Layers3 size={18}/></div><span className="metric-label">{t.satellite}</span><strong>Sentinel-2 L2A</strong><small>Earth Search · STAC catalog</small></article></div><p className="data-disclaimer"><CircleHelp size={14}/> {t.signalText}</p></section>
  <section className="split-section"><div className="section-intro"><div className="eyebrow">{t.source}</div><h2>{t.focus}</h2><p>{t.focusText}</p><button className="text-link" onClick={()=>setSection("methods")}>{t.docs}<ArrowUpRight size={15}/></button></div><div className="source-list">{[[t.nasa,"Global temperature anomaly series","NASA"],[t.power,"Daily climate variables","NASA"],[t.firms,"Active fire detections","NASA"],[t.sentinel,"Optical Earth observation","ESA / Community catalog"]].map(([name,desc,owner],i)=><div className="source-row" key={name}><span className="source-number">0{i+1}</span><div><strong>{name}</strong><small>{desc}</small></div><span className="source-owner">{owner}</span><ArrowUpRight size={15}/></div>)}</div></section>
  <section className="migration-note"><div className="note-icon"><Database size={19}/></div><div><strong>{t.note}</strong><p>{t.noteText}</p><a href="https://agrovision-mnxorykmgeisybvcnufu2q.streamlit.app/" target="_blank" rel="noreferrer">{t.legacy}<ArrowUpRight size={14}/></a></div></section>
 </>:<section className="placeholder-section"><div className="eyebrow">GUMA / RESEARCH MODULE</div><h1>{sectionTitle}</h1><p>{t.noteText}</p><div className="module-panel"><Compass size={28}/><h3>{lang==="en"?"Module migration in progress":"Migração do módulo em andamento"}</h3><p>{lang==="en"?"This research module is being migrated and validated in stages.":"Este módulo de pesquisa está sendo migrado e validado por etapas."}</p><a href="https://agrovision-mnxorykmgeisybvcnufu2q.streamlit.app/" target="_blank" rel="noreferrer">{t.legacy}<ArrowUpRight size={14}/></a></div></section>}
 <footer><span>GUMA — EARTH INTELLIGENCE</span><span>{t.footer}</span><span>© 2026</span></footer></main></div>;
}
createRoot(document.getElementById("root")).render(<App/>);
