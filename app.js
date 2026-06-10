const state = {
  chapter: "Tous",
  type: "Tous",
  year: "Tous",
  place: "Tous",
  query: "",
  sort: "recent",
  favoritesOnly: false,
  selectedId: null,
  selectedChapter: null,
  correctionVisible: false
};

const exercises = window.DNB_EXERCISES || [];
const favorites = new Set(loadFavorites());
const yearColors = {
  2018: "#d9486e",
  2019: "#e17b34",
  2020: "#d0a21f",
  2021: "#55a65a",
  2022: "#249b8e",
  2023: "#3387c8",
  2024: "#6f63c8",
  2025: "#b44bb6"
};

const officialChapters = [
  "EMC-01 : Respect de soi et des autres",
  "EMC-02 : Discriminations et égalité",
  "EMC-03 : Laïcité",
  "EMC-04 : Libertés, droits et devoirs",
  "EMC-05 : Justice et État de droit",
  "EMC-06 : Valeurs et symboles de la République",
  "EMC-07 : Citoyenneté française et européenne",
  "EMC-08 : Démocratie et participation citoyenne",
  "EMC-09 : Le vote et les élections",
  "EMC-10 : Médias, information et esprit critique",
  "EMC-11 : Défense et sécurité",
  "EMC-12 : Engagement citoyen",
  "EMC-13 : Développement durable et responsabilité citoyenne",
  "G-01 : Les aires urbaines françaises",
  "G-02 : Les espaces productifs",
  "G-03 : Les espaces de faible densité",
  "G-04 : Aménager le territoire français",
  "G-05 : Les territoires ultramarins",
  "G-06 : L'Union européenne",
  "G-07 : La France et l'Europe dans le monde",
  "H-01 : Première Guerre mondiale",
  "H-02 : Régimes totalitaires et démocraties fragilisées",
  "H-03 : Seconde Guerre mondiale",
  "H-04 : France occupée, régime de Vichy et Résistance",
  "H-05 : Décolonisation et indépendances",
  "H-06 : Guerre froide",
  "H-07 : Construction européenne",
  "H-08 : Le monde depuis 1989",
  "H-09 : Refonder la République (1944-1947)",
  "H-10 : La Ve République",
  "H-11 : Évolutions de la société française depuis les années 1950"
];

const els = {
  listPage: document.querySelector("#listPage"),
  detailPage: document.querySelector("#detailPage"),
  backButton: document.querySelector("#backButton"),
  aboutButton: document.querySelector("#aboutButton"),
  aboutOverlay: document.querySelector("#aboutOverlay"),
  aboutClose: document.querySelector("#aboutClose"),
  themeToggle: document.querySelector("#themeToggle"),
  searchInput: document.querySelector("#searchInput"),
  favoriteOnly: document.querySelector("#favoriteOnly"),
  chapterSelect: document.querySelector("#chapterSelect"),
  typeSelect: document.querySelector("#typeSelect"),
  yearSelect: document.querySelector("#yearSelect"),
  placeSelect: document.querySelector("#placeSelect"),
  sortSelect: document.querySelector("#sortSelect"),
  resetButton: document.querySelector("#resetButton"),
  resultCount: document.querySelector("#resultCount"),
  exerciseList: document.querySelector("#exerciseList"),
  viewerMeta: document.querySelector("#viewerMeta"),
  viewerTitle: document.querySelector("#viewerTitle"),
  subjectView: document.querySelector("#subjectView"),
  correctionPanel: document.querySelector("#correctionPanel"),
  correctionView: document.querySelector("#correctionView"),
  toggleCorrection: document.querySelector("#toggleCorrection")
};

applyStoredTheme();

function normalize(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function renderMarkdown(markdown) {
  if (window.marked) {
    marked.setOptions({ breaks: true, gfm: true });
    return marked.parse(markdown || "");
  }

  return `<pre>${escapeHtml(markdown || "")}</pre>`;
}

function escapeXml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getYearColor(year) {
  return yearColors[year] || "#276d61";
}

function fileSlug(value) {
  return normalize(value)
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 90) || "sujet-dnb";
}

function cleanMarkdownText(value) {
  return String(value || "")
    .replace(/<p class="cleaned-note"><strong>(.*?)<\/strong>\s*(.*?)<\/p>/g, "$1 $2")
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/<[^>]+>/g, "")
    .trim();
}

function markdownImageRefs(markdown) {
  const refs = [];
  const pattern = /!\[([^\]]*)\]\(([^)]+)\)/g;
  let match = pattern.exec(markdown);

  while (match) {
    refs.push({ alt: match[1] || "Illustration", src: match[2] });
    match = pattern.exec(markdown);
  }

  return refs;
}

async function fetchLocalAsset(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Asset introuvable : ${path}`);
  return {
    bytes: new Uint8Array(await response.arrayBuffer()),
    mime: response.headers.get("content-type") || "image/jpeg"
  };
}

async function assetsFromMarkdown(markdown) {
  const refs = markdownImageRefs(markdown);
  const assets = [];

  for (const [index, ref] of refs.entries()) {
    if (/^https?:\/\//i.test(ref.src)) continue;
    try {
      const asset = await fetchLocalAsset(ref.src);
      const extension = asset.mime.includes("png") ? "png" : "jpg";
      assets.push({
        ...ref,
        ...asset,
        name: `image-${String(index + 1).padStart(2, "0")}.${extension}`
      });
    } catch {
      // L'export reste possible même si une image locale n'est plus disponible.
    }
  }

  return assets;
}

const crcTable = (() => {
  const table = [];
  for (let index = 0; index < 256; index += 1) {
    let code = index;
    for (let bit = 0; bit < 8; bit += 1) {
      code = code & 1 ? 0xedb88320 ^ (code >>> 1) : code >>> 1;
    }
    table[index] = code >>> 0;
  }
  return table;
})();

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc = crcTable[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function bytesFromText(text) {
  return new TextEncoder().encode(text);
}

function concatBytes(chunks) {
  const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const output = new Uint8Array(total);
  let offset = 0;
  chunks.forEach((chunk) => {
    output.set(chunk, offset);
    offset += chunk.length;
  });
  return output;
}

function numberBytes(value, length) {
  const bytes = new Uint8Array(length);
  for (let index = 0; index < length; index += 1) {
    bytes[index] = (value >>> (index * 8)) & 0xff;
  }
  return bytes;
}

function zipDateParts(date = new Date()) {
  const time = (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2);
  const day = ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
  return { time, day };
}

function makeZip(files) {
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  const { time, day } = zipDateParts();

  files.forEach((file) => {
    const name = bytesFromText(file.name);
    const content = file.bytes || bytesFromText(file.content || "");
    const crc = crc32(content);
    const localHeader = concatBytes([
      numberBytes(0x04034b50, 4),
      numberBytes(20, 2),
      numberBytes(0x0800, 2),
      numberBytes(0, 2),
      numberBytes(time, 2),
      numberBytes(day, 2),
      numberBytes(crc, 4),
      numberBytes(content.length, 4),
      numberBytes(content.length, 4),
      numberBytes(name.length, 2),
      numberBytes(0, 2),
      name
    ]);
    localParts.push(localHeader, content);
    centralParts.push(concatBytes([
      numberBytes(0x02014b50, 4),
      numberBytes(20, 2),
      numberBytes(20, 2),
      numberBytes(0x0800, 2),
      numberBytes(0, 2),
      numberBytes(time, 2),
      numberBytes(day, 2),
      numberBytes(crc, 4),
      numberBytes(content.length, 4),
      numberBytes(content.length, 4),
      numberBytes(name.length, 2),
      numberBytes(0, 2),
      numberBytes(0, 2),
      numberBytes(0, 2),
      numberBytes(0, 2),
      numberBytes(0, 4),
      numberBytes(offset, 4),
      name
    ]));
    offset += localHeader.length + content.length;
  });

  const central = concatBytes(centralParts);
  const end = concatBytes([
    numberBytes(0x06054b50, 4),
    numberBytes(0, 2),
    numberBytes(0, 2),
    numberBytes(files.length, 2),
    numberBytes(files.length, 2),
    numberBytes(central.length, 4),
    numberBytes(offset, 4),
    numberBytes(0, 2)
  ]);

  return concatBytes([...localParts, central, end]);
}

function downloadBytes(filename, mime, bytes) {
  const blob = new Blob([bytes], { type: mime });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function loadFavorites() {
  try {
    return JSON.parse(localStorage.getItem("dnbFavorites") || "[]");
  } catch {
    return [];
  }
}

function loadTheme() {
  try {
    return localStorage.getItem("dnbTheme") || "light";
  } catch {
    return "light";
  }
}

function saveTheme(theme) {
  try {
    localStorage.setItem("dnbTheme", theme);
  } catch {
    // Le thème reste utilisable même si le stockage local est indisponible.
  }
}

function applyTheme(theme) {
  const isDark = theme === "dark";
  document.body.dataset.theme = isDark ? "dark" : "light";
  els.themeToggle?.setAttribute("aria-pressed", isDark ? "true" : "false");
  els.themeToggle?.setAttribute("aria-label", isDark ? "Activer le mode clair" : "Activer le mode sombre");
}

function applyStoredTheme() {
  applyTheme(loadTheme());
}

function toggleTheme() {
  const nextTheme = document.body.dataset.theme === "dark" ? "light" : "dark";
  applyTheme(nextTheme);
  saveTheme(nextTheme);
}

function openAbout() {
  els.aboutOverlay.hidden = false;
  els.aboutButton.setAttribute("aria-expanded", "true");
  els.aboutClose.focus();
}

function closeAbout() {
  els.aboutOverlay.hidden = true;
  els.aboutButton.setAttribute("aria-expanded", "false");
  els.aboutButton.focus();
}

function saveFavorites() {
  localStorage.setItem("dnbFavorites", JSON.stringify([...favorites]));
}

function isFavorite(exerciseId) {
  return favorites.has(exerciseId);
}

function toggleFavorite(exerciseId) {
  if (isFavorite(exerciseId)) {
    favorites.delete(exerciseId);
  } else {
    favorites.add(exerciseId);
  }

  saveFavorites();
  update();
}

function favoriteButtonMarkup(exercise) {
  const active = isFavorite(exercise.id);
  return `
    <button class="favorite-button" type="button" aria-pressed="${active ? "true" : "false"}" aria-label="${active ? "Retirer des favoris" : "Ajouter aux favoris"}">
      <span aria-hidden="true">${active ? "★" : "☆"}</span>
    </button>
  `;
}

function formatLabel(value) {
  const labels = {
    Geographie: "Géographie",
    Developpement: "Développement",
    "Developpement construit": "Développement construit",
    Reperes: "Repères",
    "Reperes historiques": "Repères histoire",
    "Reperes geographiques": "Repères géo"
  };

  return labels[value] || value;
}

function getChapterPrefix(chapter) {
  const normalized = normalize(chapter);
  const codedPrefix = String(chapter || "").trim().match(/^(H|G|EMC)-\d+/i);

  if (codedPrefix) {
    return codedPrefix[1].toUpperCase();
  }

  if (
    normalized.includes("premiere guerre mondiale") ||
    normalized.includes("democraties fragilisees") ||
    normalized.includes("experiences totalitaires") ||
    normalized.includes("deuxieme guerre mondiale") ||
    normalized.includes("france defaite") ||
    normalized.includes("regime de vichy") ||
    normalized.includes("independances") ||
    normalized.includes("guerre froide") ||
    normalized.includes("projet europeen") ||
    normalized.includes("apres 1989") ||
    normalized.includes("refonder la republique") ||
    normalized.includes("ve republique") ||
    normalized.includes("societe des annees")
  ) {
    return "H";
  }

  if (
    normalized.includes("aires urbaines") ||
    normalized.includes("espaces productifs") ||
    normalized.includes("faible densite") ||
    normalized.includes("amenager") ||
    normalized.includes("territoires ultra") ||
    normalized.includes("union europeenne") ||
    normalized.includes("france et l'europe") ||
    normalized.includes("france et l’europe")
  ) {
    return "G";
  }

  if (
    normalized.startsWith("emc") ||
    normalized.includes("citoyennete") ||
    normalized.includes("democratie") ||
    normalized.includes("defense") ||
    normalized.includes("engagement") ||
    normalized.includes("harcelement") ||
    normalized.includes("valeurs") ||
    normalized.includes("droits") ||
    normalized.includes("libertes")
  ) {
    return "EMC";
  }

  return "H";
}

function formatOptionLabel(value, key) {
  if (key === "chapter" && value !== "Tous") {
    if (/^(H|G|EMC)-\d+\s*:/i.test(String(value))) {
      return value;
    }

    return `${getChapterPrefix(value)} - ${value}`;
  }

  return formatLabel(value);
}

function formatChapterChip(chapter) {
  return String(chapter)
    .replace(/^EMC\s*:\s*/i, "")
    .replace(/^(H|G|EMC)-\d+\s*:\s*/i, "");
}

function chapterTitle(chapter) {
  return formatChapterChip(chapter);
}

function chapterParam(chapter) {
  return String(chapter || "").trim();
}

function uniqueValues(key) {
  if (key === "chapter") {
    return officialChapters;
  }

  const values = exercises.flatMap((exercise) => {
    if (key === "type") return exercise.types || [exercise.type];
    return [exercise[key]];
  });

  return [...new Set(values.filter(Boolean))].sort((a, b) => {
    if (key === "year") return b - a;
    if (key === "chapter") return compareChapters(a, b);
    return String(a).localeCompare(String(b), "fr");
  });
}

function compareChapters(a, b) {
  const order = { EMC: 0, G: 1, H: 2 };
  const prefixA = getChapterPrefix(a);
  const prefixB = getChapterPrefix(b);

  if (prefixA !== prefixB) {
    return order[prefixA] - order[prefixB];
  }

  const codeA = String(a).match(/^(?:H|G|EMC)-(\d+)/i);
  const codeB = String(b).match(/^(?:H|G|EMC)-(\d+)/i);

  if (codeA && codeB) {
    return Number(codeA[1]) - Number(codeB[1]);
  }

  return String(a).localeCompare(String(b), "fr");
}

function fillSelect(select, values, selectedValue, key) {
  select.innerHTML = "";
  ["Tous", ...values].forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = formatOptionLabel(value, key);
    option.selected = String(value) === String(selectedValue);
    select.append(option);
  });
}

function buildFilters() {
  fillSelect(els.chapterSelect, uniqueValues("chapter"), state.chapter, "chapter");
  fillSelect(els.typeSelect, uniqueValues("type"), state.type, "type");
  fillSelect(els.yearSelect, uniqueValues("year"), state.year, "year");
  fillSelect(els.placeSelect, uniqueValues("place"), state.place, "place");
}

function getSearchHaystack(exercise) {
  return normalize([
    exercise.title,
    exercise.subject,
    ...(exercise.subjects || []),
    exercise.chapter,
    exercise.type,
    ...(exercise.types || []),
    exercise.place,
    exercise.year,
    exercise.session,
    exercise.source,
    ...(exercise.keywords || []),
    ...(exercise.links || []).map((link) => `${link.label} ${link.url}`),
    exercise.indexedText,
    exercise.subjectMarkdown,
    exercise.correctionMarkdown
  ].join(" "));
}

function filteredExercises() {
  const query = normalize(state.query.trim());

  const filtered = exercises.filter((exercise) => {
    const matchesChapter = state.chapter === "Tous" || (exercise.chapters || [exercise.chapter]).includes(state.chapter);
    const matchesType = state.type === "Tous" || (exercise.types || [exercise.type]).includes(state.type);
    const matchesYear = state.year === "Tous" || String(exercise.year) === String(state.year);
    const matchesPlace = state.place === "Tous" || exercise.place === state.place;
    const matchesFavorite = !state.favoritesOnly || isFavorite(exercise.id);
    const matchesQuery = !query || getSearchHaystack(exercise).includes(query);

    return matchesChapter && matchesType && matchesYear && matchesPlace && matchesFavorite && matchesQuery;
  });

  return filtered.sort((a, b) => {
    if (state.sort === "oldest") return a.year - b.year || a.title.localeCompare(b.title, "fr");
    if (state.sort === "subject") return a.subject.localeCompare(b.subject, "fr") || b.year - a.year;
    return b.year - a.year || a.title.localeCompare(b.title, "fr");
  });
}

function getRouteExerciseId() {
  const hash = window.location.hash.replace(/^#/, "");
  const params = new URLSearchParams(hash);
  return params.get("sujet");
}

function getRouteChapter() {
  const hash = window.location.hash.replace(/^#/, "");
  const params = new URLSearchParams(hash);
  return params.get("chapitre");
}

function openExercise(exerciseId, chapter = "") {
  const params = new URLSearchParams();
  params.set("sujet", exerciseId);
  if (chapterParam(chapter)) {
    params.set("chapitre", chapterParam(chapter));
  }
  window.location.hash = params.toString();
}

function showListPage() {
  els.listPage.hidden = false;
  els.detailPage.hidden = true;
  state.selectedId = null;
  state.selectedChapter = null;
  state.correctionVisible = false;
  document.title = "Les annales du DNB en HG et EMC";
}

function showDetailPage(exercise, chapter = "") {
  els.listPage.hidden = true;
  els.detailPage.hidden = false;
  els.detailPage.style.setProperty("--year-color", getYearColor(exercise.year));
  state.selectedId = exercise.id;
  state.selectedChapter = chapterParam(chapter);
  document.title = `${state.selectedChapter ? `${formatChapterChip(state.selectedChapter)} - ` : ""}${exercise.title} - Annales DNB`;
  renderViewer(exercise, state.selectedChapter);
  window.scrollTo({ top: 0, behavior: "instant" });
}

function applyRoute() {
  const exerciseId = getRouteExerciseId();
  const chapter = getRouteChapter();
  const exercise = exercises.find((item) => item.id === exerciseId);

  if (exerciseId && exercise) {
    showDetailPage(exercise, chapter);
    return;
  }

  if (exerciseId && !exercise) {
    history.replaceState(null, "", window.location.pathname + window.location.search);
  }

  showListPage();
}

function renderList(items) {
  els.resultCount.textContent = `${items.length} exercice${items.length > 1 ? "s" : ""}`;
  els.exerciseList.innerHTML = "";

  if (!items.length) {
    els.exerciseList.innerHTML = `<div class="empty-state">${state.favoritesOnly ? "Aucun favori ne correspond aux filtres." : "Aucun exercice ne correspond aux filtres."}</div>`;
    return;
  }

  items.forEach((exercise) => {
    const card = document.createElement("article");
    card.className = "exercise-card";
    card.dataset.id = exercise.id;
    card.dataset.subject = exercise.subject;
    card.dataset.year = exercise.year;
    card.style.setProperty("--year-color", getYearColor(exercise.year));
    card.innerHTML = `
      <span class="year-ribbon">${escapeHtml(exercise.year)}</span>
      ${favoriteButtonMarkup(exercise)}
      <span class="card-title">${escapeHtml(exercise.title)}</span>
      <span class="tags">
        ${(exercise.chapters || [exercise.chapter]).map((chapter) => `<button class="tag chapter-tag" type="button" data-chapter="${escapeHtml(chapter)}">${escapeHtml(formatChapterChip(chapter))}</button>`).join("")}
        ${(exercise.types || []).filter((type) => type.startsWith("Reperes")).map((type) => `<span class="tag repere-tag">${escapeHtml(formatLabel(type))}</span>`).join("")}
        <span class="tag year-tag">${escapeHtml(exercise.year)}</span>
        <span class="tag place-tag">${escapeHtml(exercise.place)}</span>
      </span>
      <div class="card-actions">
        <button class="open-card-button" type="button">Ouvrir le sujet</button>
        ${exercise.primaryPdf ? `<a class="pdf-card-link" href="${escapeHtml(exercise.primaryPdf)}" target="_blank" rel="noopener" download>Télécharger le PDF</a>` : ""}
      </div>
    `;
    card.querySelector(".open-card-button").addEventListener("click", () => {
      state.correctionVisible = false;
      openExercise(exercise.id);
    });
    card.querySelectorAll(".chapter-tag").forEach((button) => {
      button.addEventListener("click", () => {
        state.correctionVisible = false;
        openExercise(exercise.id, button.dataset.chapter);
      });
    });
    card.querySelector(".favorite-button").addEventListener("click", () => {
      toggleFavorite(exercise.id);
    });
    els.exerciseList.append(card);
  });
}

function renderViewer(exercise, selectedChapter = "") {
  if (!exercise) {
    els.viewerMeta.textContent = "Selectionnez un exercice";
    els.viewerTitle.textContent = "Sujet";
    els.subjectView.innerHTML = `<p class="empty-state">Modifiez les filtres ou la recherche pour afficher un sujet.</p>`;
    els.correctionPanel.hidden = true;
    els.toggleCorrection.hidden = true;
    return;
  }

  const chapter = chapterParam(selectedChapter);
  const markdown = chapter ? buildChapterMarkdown(exercise, chapter) : exercise.subjectMarkdown;
  els.viewerMeta.innerHTML = `<span class="viewer-year">${escapeHtml(exercise.year)}</span> ${escapeHtml(exercise.subject)} · ${escapeHtml(exercise.place)} · ${chapter ? escapeHtml(formatChapterChip(chapter)) : escapeHtml(exercise.type)}`;
  els.viewerTitle.textContent = exercise.title;
  els.subjectView.innerHTML = renderDetailFavorite(exercise) + renderChapterNav(exercise, chapter) + renderQuickAccess(exercise, chapter) + renderMarkdown(markdown) + renderLinks(exercise);
  const detailFavorite = els.subjectView.querySelector(".detail-favorite .favorite-button");
  if (detailFavorite) {
    detailFavorite.addEventListener("click", () => toggleFavorite(exercise.id));
  }
  els.subjectView.querySelectorAll(".detail-chapter-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.correctionVisible = false;
      openExercise(exercise.id, button.dataset.chapter);
    });
  });
  const fullSubjectButton = els.subjectView.querySelector(".full-subject-button");
  if (fullSubjectButton) {
    fullSubjectButton.addEventListener("click", () => {
      state.correctionVisible = false;
      openExercise(exercise.id);
    });
  }
  els.subjectView.querySelectorAll(".export-option").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        await exportSubject(exercise, chapter, markdown, button.dataset.exportFormat);
      } finally {
        button.disabled = false;
      }
    });
  });

  const hasCorrection = Boolean((exercise.correctionMarkdown || "").trim());
  els.toggleCorrection.hidden = !hasCorrection;
  els.correctionPanel.hidden = !hasCorrection || !state.correctionVisible;
  els.toggleCorrection.textContent = state.correctionVisible ? "Masquer la correction" : "Afficher la correction";
  els.correctionView.innerHTML = hasCorrection ? renderMarkdown(exercise.correctionMarkdown) : "";
}

function markdownTitle(markdown) {
  const match = String(markdown || "").match(/^#\s+(.+)$/m);
  return match ? match[1].trim() : "";
}

function markdownExamCode(markdown) {
  const match = String(markdown || "").match(/\*\*Code épreuve :\*\*\s*`([^`]+)`/);
  return match ? match[1].trim() : "";
}

function exerciseSections(markdown) {
  const lines = String(markdown || "").split("\n");
  const sections = [];
  let current = null;

  lines.forEach((line) => {
    if (/^##\s+Exercice\s+\d+/i.test(line)) {
      if (current) sections.push(current);
      current = { heading: line, lines: [line] };
      return;
    }

    if (current) current.lines.push(line);
  });

  if (current) sections.push(current);

  return sections.filter((section) => {
    const body = section.lines.join("\n");
    return /(^|\n)###\s+|(^|\n)\*\*Document|(^|\n)\*\*Questions\*\*/i.test(body) || body.length > 500;
  });
}

function sectionMatchesChapter(section, chapter) {
  const normalizedChapter = normalize(chapterTitle(chapter));
  const normalizedBody = normalize(section.lines.join("\n"));
  const prefix = getChapterPrefix(chapter);

  if (normalizedChapter && normalizedBody.includes(normalizedChapter)) {
    return true;
  }

  if (prefix === "H") return normalizedBody.includes("histoire");
  if (prefix === "G") return normalizedBody.includes("geographie");
  if (prefix === "EMC") return /enseignement moral et civique|situation pratique|emc|harcelement/.test(normalizedBody);

  return false;
}

function buildChapterMarkdown(exercise, chapter) {
  const title = markdownTitle(exercise.subjectMarkdown) || exercise.title;
  const code = markdownExamCode(exercise.subjectMarkdown) || exercise.examCode || "";
  const sections = exerciseSections(exercise.subjectMarkdown);
  const matchingSections = sections.filter((item) => sectionMatchesChapter(item, chapter));
  const prefix = getChapterPrefix(chapter);
  const section = prefix === "EMC"
    ? matchingSections.find((item) => /exercice\s+3/i.test(item.heading)) || matchingSections[0]
    : matchingSections[0];
  const codeLine = code ? `**Code épreuve :** \`${code}\`\n\n` : "";

  if (!section) {
    return `# ${title}\n\n${codeLine}## Extrait : ${chapterTitle(chapter)}\n\nCette partie du sujet n'a pas pu être isolée automatiquement. Utilisez le bouton « Accéder au sujet dans son intégralité » pour consulter le sujet complet.`;
  }

  return `# ${title}\n\n${codeLine}## Extrait : ${chapterTitle(chapter)}\n\n${trimSectionForChapter(section.lines, chapter).join("\n").trim()}`;
}

function trimSectionForChapter(lines, chapter) {
  const prefix = getChapterPrefix(chapter);
  const markerByPrefix = {
    H: /^(###\s*)?histoire\s*[:\-–—]/i,
    G: /^(###\s*)?(geographie|géographie)\s*[:\-–—]/i,
    EMC: /^(###\s*)?(situation pratique|emc|enseignement moral et civique)/i
  };
  const marker = markerByPrefix[prefix];
  if (!marker) return lines;

  const start = lines.findIndex((line) => marker.test(line.trim()));
  if (start <= 0) return lines;

  let end = lines.length;
  for (let index = start + 1; index < lines.length; index += 1) {
    const current = lines[index].trim();
    if (/^##\s+Exercice\s+\d+/i.test(current)) {
      end = index;
      break;
    }
    if (/^###\s+(histoire|geographie|géographie|situation pratique|emc|enseignement moral et civique)/i.test(current)) {
      end = index;
      break;
    }
  }

  return lines.slice(start, end);
}

function exportFileBase(exercise, chapter = "") {
  return fileSlug(`${exercise.title}${chapter ? `-${chapterTitle(chapter)}` : "-sujet-integral"}`);
}

function markdownWithExportAssets(markdown, assets) {
  let output = markdown;
  assets.forEach((asset) => {
    output = output.replaceAll(`](${asset.src})`, `](assets/${asset.name})`);
  });
  return output;
}

async function exportMarkdownZip(exercise, chapter, markdown) {
  const base = exportFileBase(exercise, chapter);
  const assets = await assetsFromMarkdown(markdown);
  const md = markdownWithExportAssets(markdown, assets);
  const files = [
    { name: `${base}.md`, content: md },
    ...assets.map((asset) => ({ name: `assets/${asset.name}`, bytes: asset.bytes }))
  ];
  downloadBytes(`${base}-markdown.zip`, "application/zip", makeZip(files));
}

function markdownBlocks(markdown) {
  const blocks = [];
  const lines = cleanMarkdownText(markdown).split("\n");

  lines.forEach((line) => {
    const text = line.trim();
    const image = line.match(/!\[([^\]]*)\]\(([^)]+)\)/);

    if (image) {
      blocks.push({ type: "image", alt: image[1] || "Illustration", src: image[2] });
    } else if (/^###\s+/.test(text)) {
      blocks.push({ type: "h3", text: text.replace(/^###\s+/, "") });
    } else if (/^##\s+/.test(text)) {
      blocks.push({ type: "h2", text: text.replace(/^##\s+/, "") });
    } else if (/^#\s+/.test(text)) {
      blocks.push({ type: "h1", text: text.replace(/^#\s+/, "") });
    } else if (/^>\s+/.test(text)) {
      blocks.push({ type: "quote", text: text.replace(/^>\s+/, "") });
    } else if (/^[-•]\s+/.test(text)) {
      blocks.push({ type: "bullet", text: text.replace(/^[-•]\s+/, "") });
    } else if (/^\d+\.\s+/.test(text)) {
      blocks.push({ type: "number", text });
    } else if (text) {
      blocks.push({ type: "p", text });
    }
  });

  return blocks;
}

function docxParagraph(text, style = "") {
  const styleXml = style ? `<w:pPr><w:pStyle w:val="${style}"/></w:pPr>` : "";
  return `<w:p>${styleXml}<w:r><w:t xml:space="preserve">${escapeXml(text)}</w:t></w:r></w:p>`;
}

function docxImage(asset, relationshipId) {
  return `
    <w:p>
      <w:r>
        <w:drawing>
          <wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
            <wp:extent cx="5486400" cy="3657600"/>
            <wp:docPr id="${relationshipId.replace("rId", "")}" name="${escapeXml(asset.alt)}"/>
            <a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
              <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
                <pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">
                  <pic:nvPicPr><pic:cNvPr id="0" name="${escapeXml(asset.name)}"/><pic:cNvPicPr/></pic:nvPicPr>
                  <pic:blipFill><a:blip r:embed="${relationshipId}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>
                  <pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="5486400" cy="3657600"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>
                </pic:pic>
              </a:graphicData>
            </a:graphic>
          </wp:inline>
        </w:drawing>
      </w:r>
    </w:p>
  `;
}

async function exportDocx(exercise, chapter, markdown) {
  const base = exportFileBase(exercise, chapter);
  const assets = await assetsFromMarkdown(markdown);
  const assetBySrc = new Map(assets.map((asset, index) => [asset.src, { ...asset, relationshipId: `rId${index + 2}` }]));
  const body = markdownBlocks(markdown).map((block) => {
    if (block.type === "image") {
      const asset = assetBySrc.get(block.src);
      return asset ? docxImage(asset, asset.relationshipId) : docxParagraph(block.alt, "Quote");
    }
    if (block.type === "h1") return docxParagraph(block.text, "Heading1");
    if (block.type === "h2") return docxParagraph(block.text, "Heading2");
    if (block.type === "h3") return docxParagraph(block.text, "Heading3");
    if (block.type === "quote") return docxParagraph(block.text, "Quote");
    return docxParagraph(block.text);
  }).join("");
  const relationships = [
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>',
    ...assets.map((asset) => `<Relationship Id="${assetBySrc.get(asset.src).relationshipId}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/${asset.name}"/>`)
  ].join("");
  const files = [
    { name: "[Content_Types].xml", content: `<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="jpg" ContentType="image/jpeg"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>` },
    { name: "_rels/.rels", content: `<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>` },
    { name: "word/_rels/document.xml.rels", content: `<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${relationships}</Relationships>` },
    { name: "word/styles.xml", content: `<?xml version="1.0" encoding="UTF-8"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/></w:style><w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/></w:style><w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/></w:style></w:styles>` },
    { name: "word/document.xml", content: `<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>${body}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr></w:body></w:document>` },
    ...assets.map((asset) => ({ name: `word/media/${asset.name}`, bytes: asset.bytes }))
  ];
  downloadBytes(`${base}.docx`, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", makeZip(files));
}

function odtParagraph(text, style = "Text_20_body") {
  return `<text:p text:style-name="${style}">${escapeXml(text)}</text:p>`;
}

function odtImage(asset) {
  return `<text:p text:style-name="Text_20_body"><draw:frame draw:name="${escapeXml(asset.name)}" text:anchor-type="paragraph" svg:width="16cm" svg:height="10cm"><draw:image xlink:href="Pictures/${escapeXml(asset.name)}" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/></draw:frame></text:p>`;
}

async function exportOdt(exercise, chapter, markdown) {
  const base = exportFileBase(exercise, chapter);
  const assets = await assetsFromMarkdown(markdown);
  const assetBySrc = new Map(assets.map((asset) => [asset.src, asset]));
  const body = markdownBlocks(markdown).map((block) => {
    if (block.type === "image") {
      const asset = assetBySrc.get(block.src);
      return asset ? odtImage(asset) : odtParagraph(block.alt);
    }
    if (block.type === "h1") return odtParagraph(block.text, "Heading_20_1");
    if (block.type === "h2") return odtParagraph(block.text, "Heading_20_2");
    if (block.type === "h3") return odtParagraph(block.text, "Heading_20_3");
    return odtParagraph(block.text);
  }).join("");
  const manifestImages = assets.map((asset) => `<manifest:file-entry manifest:full-path="Pictures/${escapeXml(asset.name)}" manifest:media-type="${escapeXml(asset.mime)}"/>`).join("");
  const files = [
    { name: "mimetype", content: "application/vnd.oasis.opendocument.text" },
    { name: "META-INF/manifest.xml", content: `<?xml version="1.0" encoding="UTF-8"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2"><manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/><manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>${manifestImages}</manifest:manifest>` },
    { name: "content.xml", content: `<?xml version="1.0" encoding="UTF-8"?><office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" office:version="1.2"><office:automatic-styles/><office:body><office:text>${body}</office:text></office:body></office:document-content>` },
    ...assets.map((asset) => ({ name: `Pictures/${asset.name}`, bytes: asset.bytes }))
  ];
  downloadBytes(`${base}.odt`, "application/vnd.oasis.opendocument.text", makeZip(files));
}

async function exportSubject(exercise, chapter, markdown, format) {
  if (format === "pdf") {
    window.print();
    return;
  }

  if (format === "markdown") {
    await exportMarkdownZip(exercise, chapter, markdown);
    return;
  }

  if (format === "odt") {
    await exportOdt(exercise, chapter, markdown);
    return;
  }

  if (format === "docx") {
    await exportDocx(exercise, chapter, markdown);
  }
}

function renderDetailFavorite(exercise) {
  return `<div class="detail-favorite">${favoriteButtonMarkup(exercise)}</div>`;
}

function renderChapterNav(exercise, activeChapter = "") {
  const chapters = exercise.chapters || [exercise.chapter];
  if (!chapters.length) return "";

  return `
    <div class="chapter-nav" aria-label="Parties du sujet">
      ${chapters.map((chapter) => `<button class="tag chapter-tag detail-chapter-button" type="button" data-chapter="${escapeHtml(chapter)}" aria-pressed="${chapter === activeChapter ? "true" : "false"}">${escapeHtml(formatChapterChip(chapter))}</button>`).join("")}
    </div>
  `;
}

function renderQuickAccess(exercise, activeChapter = "") {
  return `
    <div class="quick-access">
      <details class="export-menu">
        <summary class="secondary-resource export-menu-button">Exporter</summary>
        <div class="export-options">
          <button class="export-option" type="button" data-export-format="pdf">PDF</button>
          <button class="export-option" type="button" data-export-format="markdown">Markdown ZIP</button>
          <button class="export-option" type="button" data-export-format="odt">ODT LibreOffice</button>
          <button class="export-option" type="button" data-export-format="docx">DOCX Word</button>
        </div>
      </details>
      ${activeChapter ? `<button class="primary-resource full-subject-button" type="button">Accéder au sujet dans son intégralité</button>` : ""}
      ${exercise.primaryPdf ? `<a class="primary-resource" href="${escapeHtml(exercise.primaryPdf)}" target="_blank" rel="noopener">Ouvrir le PDF officiel</a>` : ""}
    </div>
  `;
}

function renderLinks(exercise) {
  const links = exercise.links || [];
  const officialProgram = {
    label: "Programme officiel cycle 4 (2020)",
    url: "https://www.education.gouv.fr/bo/20/Hebdo31/MENE2018714A.htm"
  };
  const allLinks = [...links, officialProgram];

  const items = allLinks.map((link) => {
    return `<a class="resource-link" href="${escapeHtml(link.url)}" target="_blank" rel="noopener">${escapeHtml(link.label)}</a>`;
  }).join("");

  return `
    <div class="resource-panel">
      <div class="panel-title">Ressources officielles</div>
      <div class="resource-links">${items}</div>
    </div>
  `;
}

function update() {
  buildFilters();
  renderList(filteredExercises());
  applyRoute();
}

els.searchInput.addEventListener("input", (event) => {
  state.query = event.target.value;
  update();
});

els.aboutButton.addEventListener("click", openAbout);
els.aboutClose.addEventListener("click", closeAbout);
els.aboutOverlay.addEventListener("click", (event) => {
  if (event.target === els.aboutOverlay) {
    closeAbout();
  }
});

els.themeToggle.addEventListener("click", toggleTheme);

els.favoriteOnly.addEventListener("change", (event) => {
  state.favoritesOnly = event.target.checked;
  update();
});

[
  ["chapter", els.chapterSelect],
  ["type", els.typeSelect],
  ["year", els.yearSelect],
  ["place", els.placeSelect]
].forEach(([key, select]) => {
  select.addEventListener("change", (event) => {
    state[key] = event.target.value;
    update();
  });
});

els.sortSelect.addEventListener("change", (event) => {
  state.sort = event.target.value;
  update();
});

els.resetButton.addEventListener("click", () => {
  state.chapter = "Tous";
  state.type = "Tous";
  state.year = "Tous";
  state.place = "Tous";
  state.query = "";
  state.sort = "recent";
  state.favoritesOnly = false;
  state.selectedId = null;
  state.correctionVisible = false;
  els.searchInput.value = "";
  els.favoriteOnly.checked = false;
  els.sortSelect.value = "recent";
  update();
});

els.backButton.addEventListener("click", () => {
  history.pushState(null, "", window.location.pathname + window.location.search);
  applyRoute();
});

els.toggleCorrection.addEventListener("click", () => {
  state.correctionVisible = !state.correctionVisible;
  renderViewer(exercises.find((exercise) => exercise.id === state.selectedId), state.selectedChapter);
});

window.addEventListener("hashchange", applyRoute);
window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !els.aboutOverlay.hidden) {
    closeAbout();
  }
});

update();
