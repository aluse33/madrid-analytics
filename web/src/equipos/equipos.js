// GENERADO por rma.escudos: no editar a mano (se sobrescribe en cada `rma salidas`).
import {FileAttachment} from "observablehq:stdlib";
import {html} from "npm:htl";

export const EQUIPOS = {
 "Alaves": {
  "nombre": "Alavés",
  "corto": "ALA"
 },
 "Almeria": {
  "nombre": "Almería",
  "corto": "ALM"
 },
 "Athletic Club": {
  "nombre": "Athletic Club",
  "corto": "ATH"
 },
 "Atletico Madrid": {
  "nombre": "Atlético de Madrid",
  "corto": "ATM"
 },
 "Barcelona": {
  "nombre": "Barcelona",
  "corto": "BAR"
 },
 "Cadiz": {
  "nombre": "Cádiz",
  "corto": "CAD"
 },
 "Celta Vigo": {
  "nombre": "Celta de Vigo",
  "corto": "CEL"
 },
 "Deportivo La Coruna": {
  "nombre": "Deportivo de La Coruña",
  "corto": "DEP"
 },
 "Eibar": {
  "nombre": "Eibar",
  "corto": "EIB"
 },
 "Elche": {
  "nombre": "Elche",
  "corto": "ELC"
 },
 "Espanyol": {
  "nombre": "Espanyol",
  "corto": "ESP"
 },
 "Getafe": {
  "nombre": "Getafe",
  "corto": "GET"
 },
 "Girona": {
  "nombre": "Girona",
  "corto": "GIR"
 },
 "Granada": {
  "nombre": "Granada",
  "corto": "GRA"
 },
 "Las Palmas": {
  "nombre": "Las Palmas",
  "corto": "LPA"
 },
 "Leganes": {
  "nombre": "Leganés",
  "corto": "LEG"
 },
 "Levante": {
  "nombre": "Levante",
  "corto": "LEV"
 },
 "Malaga": {
  "nombre": "Málaga",
  "corto": "MAL"
 },
 "Mallorca": {
  "nombre": "Mallorca",
  "corto": "MLL"
 },
 "Osasuna": {
  "nombre": "Osasuna",
  "corto": "OSA"
 },
 "Racing Santander": {
  "nombre": "Racing de Santander",
  "corto": "RAC"
 },
 "Rayo Vallecano": {
  "nombre": "Rayo Vallecano",
  "corto": "RAY"
 },
 "Real Betis": {
  "nombre": "Real Betis",
  "corto": "BET"
 },
 "Real Madrid": {
  "nombre": "Real Madrid",
  "corto": "RMA"
 },
 "Real Oviedo": {
  "nombre": "Real Oviedo",
  "corto": "OVI"
 },
 "Real Sociedad": {
  "nombre": "Real Sociedad",
  "corto": "RSO"
 },
 "Real Valladolid": {
  "nombre": "Real Valladolid",
  "corto": "VLL"
 },
 "SD Huesca": {
  "nombre": "Huesca",
  "corto": "HUE"
 },
 "Sevilla": {
  "nombre": "Sevilla",
  "corto": "SEV"
 },
 "Valencia": {
  "nombre": "Valencia",
  "corto": "VAL"
 },
 "Villarreal": {
  "nombre": "Villarreal",
  "corto": "VIL"
 }
};

const ADJUNTOS = {
  "Alaves": FileAttachment("./alaves.png"),
  "Almeria": FileAttachment("./almeria.png"),
  "Athletic Club": FileAttachment("./athletic-club.png"),
  "Atletico Madrid": FileAttachment("./atletico-madrid.png"),
  "Barcelona": FileAttachment("./barcelona.png"),
  "Cadiz": FileAttachment("./cadiz.png"),
  "Celta Vigo": FileAttachment("./celta-vigo.png"),
  "Deportivo La Coruna": FileAttachment("./deportivo-la-coruna.png"),
  "Elche": FileAttachment("./elche.png"),
  "Espanyol": FileAttachment("./espanyol.png"),
  "Getafe": FileAttachment("./getafe.png"),
  "Girona": FileAttachment("./girona.png"),
  "Granada": FileAttachment("./granada.png"),
  "Las Palmas": FileAttachment("./las-palmas.png"),
  "Leganes": FileAttachment("./leganes.png"),
  "Levante": FileAttachment("./levante.png"),
  "Malaga": FileAttachment("./malaga.png"),
  "Mallorca": FileAttachment("./mallorca.png"),
  "Osasuna": FileAttachment("./osasuna.png"),
  "Racing Santander": FileAttachment("./racing-santander.png"),
  "Rayo Vallecano": FileAttachment("./rayo-vallecano.png"),
  "Real Betis": FileAttachment("./real-betis.png"),
  "Real Madrid": FileAttachment("./real-madrid.png"),
  "Real Oviedo": FileAttachment("./real-oviedo.png"),
  "Real Sociedad": FileAttachment("./real-sociedad.png"),
  "Real Valladolid": FileAttachment("./real-valladolid.png"),
  "Sevilla": FileAttachment("./sevilla.png"),
  "Valencia": FileAttachment("./valencia.png"),
  "Villarreal": FileAttachment("./villarreal.png"),
};

const iniciales = (n) => n.split(/\s+/).filter((p) => /^[A-ZÁÉÍÓÚ]/.test(p)).map((p) => p[0]).join("").slice(0, 2) || n[0];

// URL del escudo; si no hay, un círculo con las iniciales (como hace la web de referencia)
export function escudoUrl(equipo) {
  const a = ADJUNTOS[equipo];
  if (a) return a.href;
  const t = iniciales(nombre(equipo));
  return "data:image/svg+xml," + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><circle cx="20" cy="20" r="18" fill="#8a8f98"/>` +
    `<text x="20" y="25" text-anchor="middle" font-family="sans-serif" font-size="14" font-weight="700" fill="white">${t}</text></svg>`
  );
}

export const nombre = (equipo) => EQUIPOS[equipo]?.nombre ?? equipo;
export const corto = (equipo) => EQUIPOS[equipo]?.corto ?? String(equipo).slice(0, 3).toUpperCase();

// <img> del escudo
export const escudo = (equipo, size = 22) =>
  html`<img class="escudo" src=${escudoUrl(equipo)} alt="" width=${size} height=${size} style="height:${size}px;width:auto">`;

// escudo + nombre en línea (tablas, listas)
export const conEscudo = (equipo, size = 18) =>
  html`<span class="con-escudo">${escudo(equipo, size)}<span>${nombre(equipo)}</span></span>`;
