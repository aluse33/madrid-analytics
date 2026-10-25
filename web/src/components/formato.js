// Formato de números, fechas y resultados según el idioma de la página.
// Las páginas en inglés viven bajo /en/ (las genera `rma traducir`); el resto, en español.

export const EN = typeof location !== "undefined" && /\/en(\/|$)/.test(location.pathname);
export const LOC = EN ? "en-GB" : "es-ES";

export const num = (v, d = 2) =>
  v == null || Number.isNaN(+v) ? "–" : (+v).toLocaleString(LOC, {minimumFractionDigits: d, maximumFractionDigits: d});

export const pct = (v, d = 0) =>
  v == null || Number.isNaN(+v) ? "–" : (100 * v).toLocaleString(LOC, {minimumFractionDigits: d, maximumFractionDigits: d}) + (EN ? "%" : " %");

export const ent = (v) => (v == null ? "–" : Math.round(+v).toLocaleString(LOC));

const MESES = EN
  ? ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
  : ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
export const fecha = (d, anio = false) => {
  const x = d instanceof Date ? d : new Date(d);
  return `${x.getDate()} ${MESES[x.getMonth()]}${anio ? " " + x.getFullYear() : ""}`;
};
export const hora = (d) => (d instanceof Date ? d : new Date(d)).toLocaleTimeString(LOC, {hour: "2-digit", minute: "2-digit"});
export const fechaHora = (d) => `${fecha(d, true)}, ${hora(d)}`;
export const diaLargo = (d) => (d instanceof Date ? d : new Date(d)).toLocaleDateString(LOC, {weekday: "long", day: "numeric", month: "long"});

// Resultado del Madrid: V/E/D en español, W/D/L en inglés (la clase CSS sigue siendo res-V/E/D)
const LETRAS = EN ? {V: "W", E: "D", D: "L"} : {V: "V", E: "E", D: "D"};
export const letra = (r) => LETRAS[r] ?? r;

// Puesto: POR/DEF/MED/DEL en español, GK/DEF/MID/FWD en inglés
const PUESTOS = EN ? {POR: "GK", DEF: "DEF", MED: "MID", DEL: "FWD"} : {};
export const puestoTxt = (p) => PUESTOS[p] ?? p;

// Local/Visitante
export const condicionTxt = (c) => (EN ? ({Local: "Home", Visitante: "Away"})[c] ?? c : c);

// Ordinal: 1.º en español, 1st en inglés
export const ordinal = (n) => {
  if (!EN) return `${n}.º`;
  const s = n % 100 >= 11 && n % 100 <= 13 ? "th" : ({1: "st", 2: "nd", 3: "rd"})[n % 10] ?? "th";
  return `${n}${s}`;
};

// para los ejes de Plot
export const tickNum = (d) => (+d).toLocaleString(LOC);
export const tickPct = (d) => `${Math.round(100 * d)}${EN ? "%" : " %"}`;
