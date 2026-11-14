import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity, ArrowUpRight, Globe2, Layers3, Menu, Search, Satellite,
  Sprout, Waves, Wind, Flame, ChevronDown, ExternalLink, Compass,
  Database, FlaskConical, Languages, Leaf, CircleHelp
} from "lucide-react";
import "./style.css";

const copy = {
  en: {
    eyebrow: "EARTH SYSTEM INTELLIGENCE",
    title: "Read the signals.
Understand the planet.",
    intro: "A global workspace connecting climate indicators, satellite observation and agricultural systems — with sources and scientific limits in view.",
    explore: "Explore the observatory",
    docs: "Project methodology",
    overview: "Overview", climate: "Climate watch", observatory: "Earth observatory",
    agriculture: "Agro-systems", methods: "Methods & sources",
    global: "GLOBAL COVERAGE", status: "WEB EDITION · IN MIGRATION",
    signal: "A changing planet, in context",
    signalText: "GUMA brings independent Earth data streams into one research workspace. Each indicator keeps its source, time range, update cadence and interpretation limits visible.",
    temp: "Global temperature", co2: "Atmospheric CO₂", fire: "Active fire observations", satellite: "Satellite scene discovery",
    source: "DATA SOURCES", focus: "Built for evidence, not black boxes",
    focusText: "Explore the data lineage behind every layer. GUMA does not turn unrelated indicators into an unexplained score or present screening outputs as forecasts.",
    nasa: "NASA GISS · GISTEMP", power: "NASA POWER", firms: "NASA FIRMS", sentinel: "Sentinel-2 · Earth Search",
    note: "Migration note", noteText: "This Vercel edition is the new web interface in development. The existing Streamlit application remains available while analytical workflows and account features are migrated and validated.",
    legacy: "Open current research prototype", footer: "Independent research prototype · Not affiliated with or endorsed by NASA."
  },
  pt: {
    eyebrow: "INTELIGÊNCIA DO SISTEMA TERRESTRE",
    title: "Leia os sinais.
Compreenda o planeta.",
    intro: "Um ambiente global que conecta indicadores climáticos, observação por satélite e sistemas agrícolas — mantendo fontes e limites científicos à vista.",
    explore: "Explorar o observatório",
    docs: "Metodologia do projeto",
    overview: "Visão geral", climate: "Observatório climático", observatory: "Observatório da Terra",
    agriculture: "Sistemas agrícolas", methods: "Métodos e fontes",
    global: "COBERTURA GLOBAL", status: "EDIÇÃO WEB · EM MIGRAÇÃO",
    signal: "Um planeta em transformação, em contexto",
    signalText: "O GUMA reúne fluxos independentes de dados da Terra em um único ambiente de pesquisa. Cada indicador mantém visíveis sua fonte, período, frequência de atualização e limites de interpretação.",
    temp: "Temperatura global", co2: "CO₂ atmosférico", fire: "Observações de focos de fogo", satellite: "Descoberta de cenas orbitais",
    source: "FONTES DE DADOS", focus: "Feito para evidências, não para caixas-pretas",
    focusText: "Explore a linhagem dos dados por trás de cada camada. O GUMA não transforma indicadores distintos em uma pontuação inexplicável nem apresenta triagens como previsões.",
    nasa: "NASA GISS · GISTEMP", power: "NASA POWER", firms: "NASA FIRMS", sentinel: "Sentinel-2 · Earth Search",
    note: "Nota sobre a migração", noteText: "Esta edição Vercel é a nova interface web em desenvolvimento. O aplicativo Streamlit existente continua disponível enquanto os fluxos analíticos e os recursos de conta são migrados e validados.",
    legacy: "Abrir protótipo de pesquisa atual", footer: "Protótipo independente de pesquisa · Sem vínculo ou endosso da NASA."
  }
};

const nav = [
  ["overview", Globe2], ["climate", Activity], ["observatory", Satellite],
  ["agriculture", Sprout], ["methods", FlaskConical]
];

function App() {
  const [lang, setLang] = useState("en");
  const [section, setSection] = useState("overview");
  const [mobileOpen, setMobileOpen] = useState(false);
  const t = copy[lang];
  const sectionTitle = useMemo(() => t[section] || t.overview, [t, section]);

  return <div className="shell">
    <aside className={mobileOpen ? "sidebar open" : "sidebar"}>
      <a className="brand" href="#" onClick={() => setSection("overview")}>
        <span className="brand-mark"><Waves size={24}/></span>
        <span><strong>GUMA</strong><small>EARTH INTELLIGENCE</small></span>
      </a>
      <div className="side-label">WORKSPACE</div>
      <nav>{nav.map(([key, Icon]) => <button key={key} className={section === key ? "nav-item active" : "nav-item"} onClick={() => {setSection(key);setMobileOpen(false);}}>
        <Icon size={17}/><span>{t[key]}</span>{section === key && <span className="nav-dot"/>}
      </button>)}</nav>
      <div className="side-bottom">
        <div className="global-pill"><Globe2 size={15}/><span>{t.global}</span></div>
        <p>Earth data · Climate · Agriculture</p>
        <a href="https://github.com/interpessoal21-ops/agrovision" target="_blank" rel="noreferrer">GitHub repository <ExternalLink size={12}/></a>
      </div>
    </aside>

    <main className="main">
      <header className="topbar">
        <button className="mobile-menu" onClick={() => setMobileOpen(!mobileOpen)} aria-label="Toggle navigation"><Menu/></button>
        <div className="crumb"><span>GUMA</span><i>/</i>{sectionTitle}</div>
        <div className="top-actions">
          <span className="status"><span/> {t.status}</span>
          <button className="lang" onClick={() => setLang(lang === "en" ? "pt" : "en")}><Languages size={15}/>{lang.toUpperCase()}</button>
        </div>
      </header>

      {section === "overview" ? <>
        <section className="hero">
          <div className="hero-grid"/>
          <div className="hero-copy">
            <div className="eyebrow"><span/> {t.eyebrow}</div>
            <h1>{t.title.split("\n").map((line,i)=><React.Fragment key={i}>{i>0&&<br/>}{line}</React.Fragment>)}</h1>
            <p>{t.intro}</p>
            <div className="hero-actions">
              <button className="primary" onClick={() => setSection("observatory")}>{t.explore}<ArrowUpRight size={16}/></button>
              <button className="secondary" onClick={() => setSection("methods")}>{t.docs}<ExternalLink size={14}/></button>
            </div>
          </div>
          <div className="hero-art" aria-hidden="true">
            <div className="orb orb-one"/><div className="orb orb-two"/>
            <div className="globe"><div className="latitude lat-one"/><div className="latitude lat-two"/><div className="longitude lon-one"/><div className="longitude lon-two"/><div className="land land-one"/><div className="land land-two"/></div>
            <div className="orbit orbit-one"/><div className="orbit orbit-two"/>
            <div className="orbit-label label-a"><Satellite size={14}/> EARTH OBSERVATION</div>
            <div className="orbit-label label-b"><Wind size={14}/> CLIMATE SIGNALS</div>
          </div>
          <div className="hero-index"><span>01</span><span> / </span><span>05</span></div>
        </section>

        <section className="metrics">
          <div className="metric-head"><span>01 / {t.signal}</span><span>GLOBAL SYSTEMS</span></div>
          <div className="metric-grid">
            <article className="metric-card"><div className="metric-icon"><Activity size={18}/></div><span className="metric-label">{t.temp}</span><strong>GISTEMP v4</strong><small>1880 — present · Monthly & annual</small><div className="sparkline"><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/></div></article>
            <article className="metric-card"><div className="metric-icon"><Wind size={18}/></div><span className="metric-label">{t.co2}</span><strong>Mauna Loa · CO₂</strong><small>Monthly station observations · ppm</small><div className="sparkline alt"><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/><i/></div></article>
            <article className="metric-card"><div className="metric-icon"><Flame size={18}/></div><span className="metric-label">{t.fire}</span><strong>VIIRS · FIRMS</strong><small>Rolling observations · Global</small><div className="metric-foot"><span className="live-dot"/> SOURCE CONNECTOR</div></article>
            <article className="metric-card"><div className="metric-icon"><Layers3 size={18}/></div><span className="metric-label">{t.satellite}</span><strong>Sentinel-2 L2A</strong><small>Earth Search · STAC catalog</small><div className="metric-foot"><span className="live-dot"/> SOURCE CONNECTOR</div></article>
          </div>
          <p className="data-disclaimer"><CircleHelp size={14}/> Indicators shown here identify connected datasets; live values and analytical controls are being migrated into this web edition.</p>
        </section>

        <section className="split-section">
          <div className="section-intro"><div className="eyebrow">{t.source}</div><h2>{t.focus}</h2><p>{t.focusText}</p><button className="text-link" onClick={() => setSection("methods")}>{t.docs}<ArrowUpRight size={15}/></button></div>
          <div className="source-list">
            {[[t.nasa,"Global temperature anomaly series","NASA"],[t.power,"Daily climate variables","NASA"],[t.firms,"Active fire detections","NASA"],[t.sentinel,"Optical Earth observation","ESA / Community catalog"]].map(([name,desc,owner],i)=><div className="source-row" key={name}><span className="source-number">0{i+1}</span><div><strong>{name}</strong><small>{desc}</small></div><span className="source-owner">{owner}</span><ArrowUpRight size={15}/></div>)}
          </div>
        </section>
        <section className="migration-note"><div className="note-icon"><Database size={19}/></div><div><strong>{t.note}</strong><p>{t.noteText}</p><a href="https://agrovision-mnxorykmgeisybvcnufu2q.streamlit.app/" target="_blank" rel="noreferrer">{t.legacy}<ArrowUpRight size={14}/></a></div></section>
      </> : <section className="placeholder-section">
        <div className="eyebrow">GUMA / RESEARCH MODULE</div>
        <h1>{sectionTitle}</h1>
        <p>{t.noteText}</p>
        <div className="module-panel"><Compass size={28}/><h3>{lang === "en" ? "Module migration in progress" : "Migração do módulo em andamento"}</h3><p>{lang === "en" ? "The web interface is being built in stages. The current Streamlit prototype remains the reference implementation for this workflow." : "A interface web está sendo construída por etapas. O protótipo Streamlit atual continua sendo a implementação de referência deste fluxo."}</p><a href="https://agrovision-mnxorykmgeisybvcnufu2q.streamlit.app/" target="_blank" rel="noreferrer">{t.legacy}<ArrowUpRight size={14}/></a></div>
      </section>}

      <footer><span>GUMA — EARTH INTELLIGENCE</span><span>{t.footer}</span><span>© 2026</span></footer>
    </main>
  </div>;
}

createRoot(document.getElementById("root")).render(<App/>);