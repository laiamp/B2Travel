// popup.js — Travel Saver popup logic

const STORAGE_KEY = "travelItems";

// ---- State ----
let currentTab = "pages";
let allItems = [];

// ---- DOM refs ----
const itemCountEl = document.getElementById("itemCount");
const btnSavePage = document.getElementById("btnSavePage");
const btnSaveSong = document.getElementById("btnSaveSong");
const btnSaveText = document.getElementById("btnSaveText");
const textInput = document.getElementById("textInput");
const photoInput = document.getElementById("photoInput");
const photoGrid = document.getElementById("photoGrid");
const pagesList = document.getElementById("pagesList");
const textsList = document.getElementById("textsList");
const songsList = document.getElementById("songsList");
const pagesEmpty = document.getElementById("pagesEmpty");
const textsEmpty = document.getElementById("textsEmpty");
const photosEmpty = document.getElementById("photosEmpty");
const songsEmpty = document.getElementById("songsEmpty");

// ---- Init ----
document.addEventListener("DOMContentLoaded", async () => {
    await loadItems();
    renderAll();
    setupTabs();
    setupSaveHandlers();
    setupPhotoUpload();
    await detectYouTube();
});

// ---- Storage helpers ----
async function loadItems() {
    const result = await chrome.storage.local.get(STORAGE_KEY);
    allItems = result[STORAGE_KEY] || [];
}

async function persistItems() {
    await chrome.storage.local.set({ [STORAGE_KEY]: allItems });
}

async function addItem(item) {
    allItems.unshift(item);
    await persistItems();
    updateCount();
}

// ---- YouTube helpers ----
function extractYouTubeId(url) {
    try {
        const u = new URL(url);
        if (u.hostname.includes("youtube.com")) {
            return u.searchParams.get("v") || null;
        }
        if (u.hostname === "youtu.be") {
            return u.pathname.slice(1).split("?")[0] || null;
        }
    } catch { }
    return null;
}

function ytThumbnail(videoId) {
    return `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`;
}

async function detectYouTube() {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab || !tab.url) return;
        const videoId = extractYouTubeId(tab.url);
        if (videoId) {
            btnSaveSong.style.display = "";
            btnSaveSong.dataset.videoId = videoId;
            btnSaveSong.dataset.title = tab.title || "YouTube Video";
            btnSaveSong.dataset.url = tab.url;
            // Try to get channel from page title (format: "Song - Channel - YouTube")
            const parts = (tab.title || "").split(" - ");
            btnSaveSong.dataset.channel = parts.length >= 2 ? parts.slice(1, -1).join(" - ") : "YouTube";
        }
    } catch { }
}

async function removeItem(id) {
    allItems = allItems.filter(i => i.id !== id);
    await persistItems();
    renderAll();
}

function updateCount() {
    itemCountEl.textContent = `${allItems.length} saved`;
}

// ---- Tabs ----
function setupTabs() {
    document.querySelectorAll(".tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(p => p.classList.remove("active"));
            tab.classList.add("active");
            const panel = document.getElementById("panel" + cap(tab.dataset.tab));
            panel.classList.add("active");
            currentTab = tab.dataset.tab;
        });
    });
}

function cap(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// ---- Save handlers ----
function setupSaveHandlers() {
    // Save YouTube song
    btnSaveSong.addEventListener("click", async () => {
        const videoId = btnSaveSong.dataset.videoId;
        if (!videoId) { showToast("⚠️ No YouTube video detected"); return; }
        const item = {
            id: Date.now().toString(),
            type: "song",
            videoId,
            title: btnSaveSong.dataset.title.replace(/ - YouTube$/, ""),
            channel: btnSaveSong.dataset.channel,
            thumbnail: ytThumbnail(videoId),
            url: btnSaveSong.dataset.url,
            date: new Date().toISOString()
        };
        await addItem(item);
        renderSongs();
        showToast("🎵 Song saved!");
        document.getElementById("tabSongs").click();
    });

    // Save current page
    btnSavePage.addEventListener("click", async () => {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab || !tab.url || tab.url.startsWith("chrome://")) {
            showToast("⚠️ Can't save this page");
            return;
        }
        const item = {
            id: Date.now().toString(),
            type: "page",
            url: tab.url,
            title: tab.title || tab.url,
            favicon: `https://www.google.com/s2/favicons?sz=64&domain=${new URL(tab.url).hostname}`,
            date: new Date().toISOString()
        };
        await addItem(item);
        renderPages();
        showToast("✈️ Page saved!");

        // Switch to pages tab to show the result
        document.getElementById("tabPages").click();
    });

    // Save text note
    btnSaveText.addEventListener("click", async () => {
        const content = textInput.value.trim();
        if (!content) { showToast("Type something first!"); return; }
        const item = {
            id: Date.now().toString(),
            type: "text",
            content,
            date: new Date().toISOString()
        };
        textInput.value = "";
        await addItem(item);
        renderTexts();
        showToast("📝 Note saved!");
    });

    textInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) btnSaveText.click();
    });
}

// ---- Photo upload ----
function setupPhotoUpload() {
    photoInput.addEventListener("change", async (e) => {
        const files = Array.from(e.target.files);
        for (const file of files) {
            const dataUrl = await fileToDataUrl(file);
            const item = {
                id: Date.now().toString() + Math.random().toString(36).slice(2),
                type: "photo",
                dataUrl,
                name: file.name,
                date: new Date().toISOString()
            };
            await addItem(item);
            ingestImage(file, file.name); // fire-and-forget
        }
        renderPhotos();
        showToast(`📸 ${files.length} photo${files.length > 1 ? "s" : ""} saved!`);
        photoInput.value = "";
    });

    // Drag and drop
    const area = document.getElementById("photoUploadArea");
    area.addEventListener("dragover", (e) => { e.preventDefault(); area.style.borderColor = "var(--accent)"; });
    area.addEventListener("dragleave", () => { area.style.borderColor = ""; });
    area.addEventListener("drop", async (e) => {
        e.preventDefault();
        area.style.borderColor = "";
        const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith("image/"));
        for (const file of files) {
            const dataUrl = await fileToDataUrl(file);
            const item = {
                id: Date.now().toString() + Math.random().toString(36).slice(2),
                type: "photo",
                dataUrl,
                name: file.name,
                date: new Date().toISOString()
            };
            await addItem(item);
            ingestImage(file, file.name); // fire-and-forget
        }
        renderPhotos();
        showToast(`📸 ${files.length} photo${files.length > 1 ? "s" : ""} saved!`);
    });
}

function fileToDataUrl(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = e => resolve(e.target.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// ---- Backend ingestion ----
const INGEST_URL = "http://localhost:8000/ingest/image";

/**
 * Fire-and-forget POST to the embeddings backend.
 * Accepts a File or Blob. Never throws — saving always succeeds even if backend is down.
 */
async function ingestImage(fileOrBlob, filename) {
    try {
        const form = new FormData();
        form.append("image", fileOrBlob, filename || "image.jpg");
        const res = await fetch(INGEST_URL, { method: "POST", body: form });
        if (!res.ok) console.warn("[Travel Saver] Ingest failed:", res.status, await res.text());
        else console.log("[Travel Saver] Ingested:", filename);
    } catch (err) {
        console.warn("[Travel Saver] Backend unreachable, skipping ingest:", err.message);
    }
}

// ---- Renderers ----
function renderAll() {
    renderPages();
    renderTexts();
    renderPhotos();
    renderSongs();
    updateCount();
}

function renderPages() {
    const pages = allItems.filter(i => i.type === "page");

    // Remove old cards, keep empty state
    Array.from(pagesList.children).forEach(c => { if (c !== pagesEmpty) c.remove(); });

    if (pages.length === 0) {
        pagesEmpty.style.display = "";
        return;
    }
    pagesEmpty.style.display = "none";

    pages.forEach(item => {
        const card = document.createElement("div");
        card.className = "page-card";
        card.innerHTML = `
      <img class="page-favicon" src="${esc(item.favicon)}" alt="" onerror="this.style.display='none'" />
      <div class="page-info">
        <a class="page-title" href="${esc(item.url)}" target="_blank" title="${esc(item.title)}">${esc(item.title)}</a>
        <span class="page-url">${esc(item.url)}</span>
        <span class="page-date">${formatDate(item.date)}</span>
      </div>
      <button class="btn-delete" data-id="${esc(item.id)}" title="Remove">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>`;
        card.querySelector(".btn-delete").addEventListener("click", e => {
            e.preventDefault();
            removeItem(item.id);
        });
        // Open link handler
        card.querySelector(".page-title").addEventListener("click", (e) => {
            e.preventDefault();
            chrome.tabs.create({ url: item.url });
        });
        pagesList.appendChild(card);
    });
}

function renderTexts() {
    const texts = allItems.filter(i => i.type === "text");
    Array.from(textsList.children).forEach(c => { if (c !== textsEmpty) c.remove(); });

    if (texts.length === 0) {
        textsEmpty.style.display = "";
        return;
    }
    textsEmpty.style.display = "none";

    texts.forEach(item => {
        const card = document.createElement("div");
        card.className = "text-card";
        card.innerHTML = `
      <p class="text-content">${esc(item.content)}</p>
      ${item.sourceUrl ? `<a class="text-source" href="${esc(item.sourceUrl)}" target="_blank">from ${esc(item.sourceUrl)}</a>` : ""}
      <span class="page-date" style="margin-top:6px">${formatDate(item.date)}</span>
      <button class="btn-delete" data-id="${esc(item.id)}" title="Remove">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>`;
        card.querySelector(".btn-delete").addEventListener("click", () => removeItem(item.id));
        if (item.sourceUrl) {
            card.querySelector(".text-source").addEventListener("click", (e) => {
                e.preventDefault();
                chrome.tabs.create({ url: item.sourceUrl });
            });
        }
        textsList.appendChild(card);
    });
}

function renderPhotos() {
    const photos = allItems.filter(i => i.type === "photo");
    Array.from(photoGrid.children).forEach(c => { if (c !== photosEmpty) c.remove(); });

    if (photos.length === 0) {
        photosEmpty.style.display = "";
        return;
    }
    photosEmpty.style.display = "none";

    photos.forEach(item => {
        const wrap = document.createElement("div");
        wrap.className = "photo-thumb-wrap";
        wrap.innerHTML = `
      <img class="photo-thumb" src="${item.dataUrl}" alt="${esc(item.name)}" />
      <span class="photo-name">${esc(item.name)}</span>
      <button class="btn-delete" title="Remove">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>`;
        wrap.querySelector(".btn-delete").addEventListener("click", () => removeItem(item.id));
        // Click to open full image
        wrap.querySelector(".photo-thumb").addEventListener("click", () => {
            const w = window.open();
            w.document.write(`<img src="${item.dataUrl}" style="max-width:100%;height:auto;" />`);
        });
        photoGrid.appendChild(wrap);
    });
}

function renderSongs() {
    const songs = allItems.filter(i => i.type === "song");
    Array.from(songsList.children).forEach(c => { if (c !== songsEmpty) c.remove(); });

    if (songs.length === 0) {
        songsEmpty.style.display = "";
        return;
    }
    songsEmpty.style.display = "none";

    songs.forEach(item => {
        const card = document.createElement("div");
        card.className = "song-card";
        card.innerHTML = `
      <div class="song-thumb-wrap">
        <img class="song-thumb"
             src="${esc(item.thumbnail)}"
             alt="${esc(item.title)}"
             onerror="this.style.background='#1a2235'" />
        <div class="song-play-overlay">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="white" stroke="none">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
        </div>
      </div>
      <div class="song-info">
        <span class="song-title" title="${esc(item.title)}">${esc(item.title)}</span>
        <span class="song-channel">${esc(item.channel || "")}</span>
        <span class="song-date">${formatDate(item.date)}</span>
      </div>
      <button class="btn-delete" title="Remove">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>`;
        card.querySelector(".btn-delete").addEventListener("click", e => {
            e.stopPropagation();
            removeItem(item.id);
        });
        card.addEventListener("click", () => {
            chrome.tabs.create({ url: item.url });
        });
        songsList.appendChild(card);
    });
}

// ---- Utils ----
function esc(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function showToast(message) {
    let toast = document.querySelector(".toast");
    if (!toast) {
        toast = document.createElement("div");
        toast.className = "toast";
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.remove("show"), 2200);
}
