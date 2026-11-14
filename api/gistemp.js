export default async function handler(request, response) {
  try {
    const upstream = await fetch("https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv", {
      headers: { "User-Agent": "GUMA-Earth-Intelligence/1.0", "Accept": "text/csv,text/plain" },
      signal: AbortSignal.timeout(25000)
    });
    if (!upstream.ok) throw new Error("NASA GISTEMP respondeu HTTP " + upstream.status);
    const text = await upstream.text();
    if (!text || text.slice(0, 500).toLowerCase().includes("<html")) throw new Error("A NASA não retornou o CSV esperado.");
    const lines = text.replace(/^\uFEFF/, "").trim().split(/\r?\n/);
    const headerIndex = lines.findIndex(line => line.split(",").some(cell => cell.trim() === "Year") && line.split(",").some(cell => cell.trim() === "J-D"));
    if (headerIndex < 0) throw new Error("Não foi possível reconhecer as colunas Year e J-D do GISTEMP.");
    const headers = lines[headerIndex].split(",").map(x => x.trim());
    const yi = headers.indexOf("Year"), vi = headers.indexOf("J-D");
    const rows = lines.slice(headerIndex + 1).map(line => {
      const cells = line.split(",");
      return { year: Number(cells[yi]), value: Number(cells[vi]) };
    }).filter(row => Number.isInteger(row.year) && Number.isFinite(row.value) && row.value > -90 && row.value < 90);
    if (rows.length < 8) throw new Error("A série GISTEMP retornou menos de oito observações válidas.");
    response.setHeader("Cache-Control", "s-maxage=3600, stale-while-revalidate=86400");
    response.status(200).json({ source: "NASA GISS GISTEMP v4", retrieved_at: new Date().toISOString(), rows });
  } catch (error) {
    response.status(502).json({ error: "NASA GISTEMP indisponível: " + error.message });
  }
}