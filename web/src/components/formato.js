// Formato en español (12,3 y no 12.3) para textos, tablas y ejes.

export const num = (v, d = 2) =>
  v == null || Number.isNaN(+v) ? "–" : (+v).toLocaleString("es-ES", {minimumFractionDigits: d, maximumFractionDigits: d});

export const pct = (v, d = 0) =>
  v == null || Number.isNaN(+v) ? "–" : (100 * v).toLocaleString("es-ES", {minimumFractionDigits: d, maximumFractionDigits: d}) + " %";

export const ent = (v) => (v == null ? "–" : Math.round(+v).toLocaleString("es-ES"));

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
export const fecha = (d, anio = false) => {
  const x = d instanceof Date ? d : new Date(d);
  return `${x.getDate()} ${MESES[x.getMonth()]}${anio ? " " + x.getFullYear() : ""}`;
};
export const fechaHora = (d) => {
  const x = d instanceof Date ? d : new Date(d);
  return `${fecha(x, true)}, ${x.toLocaleTimeString("es-ES", {hour: "2-digit", minute: "2-digit"})}`;
};

// para los ejes de Plot
export const tickNum = (d) => (+d).toLocaleString("es-ES");
export const tickPct = (d) => `${Math.round(100 * d)} %`;
