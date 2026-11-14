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
function TrendDetective({lang}){
 const [rows,setRows]=useState([]),[source,setSource]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState(""),[result,setResult]=useState(null);
 const [start,setStart]=useState(""),[end,setEnd]=useState("");
 const t=lang==="pt";
 const selected=useMemo(()=>rows.filter(r=>(!start||r.year>=Number(start))&&(!end||r.year<=Number(end))),[rows,start,end]);
 const loadNASA=async()=>{setBusy(true);setError("");setResult(null);try{const r=await fetch("/api/gistemp");const j=await r.json();if(!r.ok)throw new Error(j.error||"Falha ao consultar NASA GISTEMP.");setRows(j.rows);setSource("NASA GISS · GISTEMP v4");setStart(String(j.rows[0].year));setEnd(String(j.rows[j.rows.length-1].year));}catch(e){setError(e.message+" Você ainda pode importar uma série anual em CSV.");}finally{setBusy(false);}};
 const upload=async file=>{setError("");setResult(null);try{const raw=await file.text();const lines=raw.trim().split(/\r?\n/);const headers=lines.shift().split(",").map(x=>x.trim().replace(/^["']|["']$/g,""));const yi=headers.findIndex(x=>/^(year|ano)$/i.test(x)),vi=headers.findIndex((x,i)=>i!==yi&&/^(value|valor|anomaly|anomalia|indicator|indicador)$/i.test(x));if(yi<0||vi<0)throw new Error("O CSV precisa ter colunas chamadas year/ano e value/valor (ou anomaly/anomalia).");const parsed=lines.map(line=>{const c=line.split(",");return {year:Number(c[yi]),value:Number(c[vi])};}).filter(x=>Number.isFinite(x.year)&&Number.isFinite(x.value));if(parsed.length<8)throw new Error("O arquivo contém menos de oito linhas anuais válidas.");parsed.sort((a,b)=>a.year-b.year);setRows(parsed);setSource("Arquivo enviado · "+file.name);setStart(String(parsed[0].year));setEnd(String(parsed[parsed.length-1].year));}catch(e){setError(e.message);}};
 const run=()=>{try{setResult(analyze(selected));setError("");}catch(e){setResult(null);setError(e.message);}};
 return <section className="trend-workspace">
  <div className="eyebrow">GUMA / EARTH SYSTEM TREND DETECTIVE</div>
  <h1>{t?"Investigue uma tendência ambiental.":"Investigate an Earth-system trend."}</h1>
  <p className="trend-lead">{t?"Analise séries anuais com Mann–Kendall e inclinação de Sen. Comece pela série global de temperatura da NASA ou envie seu próprio CSV.":"Analyze annual series with Mann–Kendall and Sen's slope. Start with NASA's global temperature series or upload your own CSV."}</p>
  <div className="trend-controls">
   <button className="primary" onClick={loadNASA} disabled={busy}><RefreshCw size={16}/>{busy?(t?"Consultando NASA…":"Retrieving NASA…"):(t?"Carregar NASA GISTEMP":"Load NASA GISTEMP")}</button>
   <label className="upload-control"><Upload size={16}/>{t?"Enviar CSV anual":"Upload annual CSV"}<input type="file" accept=".csv,text/csv" onChange={e=>e.target.files?.[0]&&upload(e.target.files[0])}/></label>
  </div>
  {source&&<div className="dataset-meta"><Database size={15}/><span><b>{t?"Fonte":"Source"}:</b> {source} · {rows.length} {t?"observações":"observations"} · {rows[0]?.year}–{rows[rows.length-1]?.year}</span></div>}
  {rows.length>0&&<div className="analysis-panel">
   <h2>{t?"Janela de análise":"Analysis window"}</h2>
   <div className="year-controls"><label>{t?"Ano inicial":"First year"}<input type="number" value={start} onChange={e=>setStart(e.target.value)}/></label><label>{t?"Ano final":"Last year"}<input type="number" value={end} onChange={e=>setEnd(e.target.value)}/></label><button className="primary" onClick={run}>{t?"Analisar tendência":"Analyze trend"}</button></div>
   <p className="subtle">{selected.length} {t?"observações no intervalo selecionado":"observations in selected interval"}</p>
  </div>}
  {error&&<div className="error-panel" role="alert">{error}</div>}
  {result&&<div className="results-panel">
   <div className="result-heading"><div><div className="eyebrow">{t?"RESULTADO ESTATÍSTICO":"STATISTICAL RESULT"}</div><h2>{result.direction}</h2></div><span className={result.significant?"significance yes":"significance"}>{result.significant?(t?"Significativo · α = 0,05":"Significant · α = 0.05"):(t?"Não significativo · α = 0,05":"Not significant · α = 0.05")}</span></div>
   <div className="result-metrics"><article><small>Sen's slope</small><b>{result.slope.toFixed(4)}</b><span>{t?"unidades por ano":"units per year"}</span></article><article><small>Mann–Kendall τ</small><b>{result.tau.toFixed(3)}</b><span>{t?"associação monotônica":"monotonic association"}</span></article><article><small>p-value</small><b>{result.p.toPrecision(4)}</b><span>two-sided</span></article><article><small>n</small><b>{result.n}</b><span>{t?"anos válidos":"valid years"}</span></article></div>
   <div className="chart-panel"><h3>{t?"Série anual observada":"Observed annual series"}</h3><svg viewBox="0 0 760 260" role="img" aria-label="Annual observations line chart"><line x1="44" y1="12" x2="44" y2="220" stroke="currentColor" opacity=".35"/><line x1="44" y1="220" x2="740" y2="220" stroke="currentColor" opacity=".35"/><polyline fill="none" stroke="#17647a" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" points={result.data.map((d,i)=>{const min=Math.min(...result.data.map(x=>x.value)),max=Math.max(...result.data.map(x=>x.value)),x=44+i*696/Math.max(1,result.n-1),y=204-(d.value-min)/(max-min||1)*180;return x.toFixed(1)+","+y.toFixed(1)}).join(" ")}/><text x="44" y="245" fill="currentColor" fontSize="12">{result.data[0].year}</text><text x="740" y="245" textAnchor="end" fill="currentColor" fontSize="12">{result.data[result.n-1].year}</text></svg></div>
   <details className="method-details"><summary>{t?"Método e limites de interpretação":"Method and interpretation limits"}</summary><p>{t?"Mann–Kendall testa associação monotônica; a inclinação de Sen é a mediana das inclinações entre todos os pares de observações. O p-valor usa aproximação normal com correção de continuidade e correção para empates.":"Mann–Kendall tests monotonic association; Sen's slope is the median of all pairwise slopes. The p-value uses a normal approximation with continuity and tie corrections."}</p><p>{t?"Limitação importante: esta versão não corrige autocorrelação serial, não calcula intervalos de confiança e não demonstra causalidade. Uma tendência estatística não identifica seu mecanismo físico.":"Important limitation: this version does not correct for serial autocorrelation, calculate confidence intervals, or establish causation. A statistical trend does not identify its physical mechanism."}</p><p>{t?"Verifique a procedência, cobertura, alterações de medição e contexto físico antes de interpretar o resultado.":"Check provenance, coverage, measurement changes and physical context before interpreting results."}</p></details>
  </div>}
  <div className="scope-note"><CircleHelp size={16}/><span>{t?"O módulo analisa séries anuais. A série GISTEMP é uma média global de anomalias de temperatura, não uma estimativa local.":"This module analyzes annual series. GISTEMP is a global mean temperature-anomaly series, not a local estimate."}</span></div>
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
