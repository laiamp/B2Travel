// popup.js — Travel Saver popup logic
// Photos & Texts → backend API (MongoDB via FastAPI)
// Pages & Songs   → chrome.storage.local

const API_BASE = "http://127.0.0.1:8000";
const LOCAL_KEY = "travelLocalItems"; // only pages + songs

// ---- State ----
let currentTab = "pages";
let localItems = [];   // pages + songs (chrome.storage.local)
let apiPhotos = [];   // loaded from GET /retrieve/images
let apiTexts = [];   // loaded from GET /retrieve/texts

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
const globalLoader = document.getElementById("globalLoader");
const btnLogin = document.getElementById("btnLogin");
const userInfo = document.getElementById("userInfo");
const userAvatar = document.getElementById("userAvatar");
const userName = document.getElementById("userName");

function showLoader() { globalLoader.style.display = "flex"; }
function hideLoader() { globalLoader.style.display = "none"; }

// ---- Init ----
document.addEventListener("DOMContentLoaded", async () => {
    await Promise.all([loadLocalItems(), loadApiPhotos(), loadApiTexts()]);
    renderAll();
    setupTabs();
    setupSaveHandlers();
    setupPhotoUpload();
    setupAuth();
    await detectYouTube();
});

// ============================================================
// LOCAL STORAGE  (pages + songs only)
// ============================================================
async function loadLocalItems() {
    const result = await chrome.storage.local.get(LOCAL_KEY);
    localItems = result[LOCAL_KEY] || [];
}

async function persistLocalItems() {
    await chrome.storage.local.set({ [LOCAL_KEY]: localItems });
}

async function addLocalItem(item) {
    localItems.unshift(item);
    await persistLocalItems();
    updateCount();
}

async function removeLocalItem(id) {
    localItems = localItems.filter(i => i.id !== id);
    await persistLocalItems();
    renderAll();
}

// ============================================================
// BACKEND API  (photos + texts)
// ============================================================
async function loadApiPhotos() {
    try {
        const res = await fetch(`${API_BASE}/retrieve/images`);
        if (res.ok) apiPhotos = await res.json();
        else console.warn("[Travel Saver] Could not load photos from API:", res.status);
    } catch (e) {
        console.warn("[Travel Saver] Backend unreachable (photos):", e.message);
    }
}

async function loadApiTexts() {
    try {
        const res = await fetch(`${API_BASE}/retrieve/texts`);
        if (res.ok) apiTexts = await res.json();
        else console.warn("[Travel Saver] Could not load texts from API:", res.status);
    } catch (e) {
        console.warn("[Travel Saver] Backend unreachable (texts):", e.message);
    }
}

async function postText(content) {
    const form = new FormData();
    form.append("text", content);
    const res = await fetch(`${API_BASE}/ingest/text`, { method: "POST", body: form });
    if (!res.ok) throw new Error(`Ingest text failed: ${res.status}`);
    return res.json(); // { id, text, embedding_dim, collection }
}

async function postImage(fileOrBlob, filename) {
    const form = new FormData();
    form.append("image", fileOrBlob, filename || "image.jpg");
    const res = await fetch(`${API_BASE}/ingest/image`, { method: "POST", body: form });
    if (!res.ok) throw new Error(`Ingest image failed: ${res.status}`);
    return res.json(); // { id, filename, embedding_dim, collection }
}

async function deleteApiItem(collection, id) {
    const res = await fetch(`${API_BASE}/delete/${collection}/${encodeURIComponent(id)}`, {
        method: "DELETE",
    });

    if (!res.ok) {
        let detail = `Delete ${collection} failed: ${res.status}`;
        try {
            const body = await res.json();
            if (body?.detail) detail = body.detail;
        } catch { }
        throw new Error(detail);
    }
}

// ============================================================
// SHARED COUNT
// ============================================================
function updateCount() {
    const total = localItems.length + apiPhotos.length + apiTexts.length;
    itemCountEl.textContent = `${total} saved`;
}

// ============================================================
// AUTHENTICATION (Google Sign-In)
// ============================================================
async function setupAuth() {
    // Check if user info is cached
    const { userData } = await chrome.storage.local.get("userData");
    if (userData) {
        showUserInfo(userData);
    }

    btnLogin.addEventListener("click", async () => {
        try {
            // Get token from Chrome
            // Note: This requires "oauth2" client_id in manifest.json
            chrome.identity.getAuthToken({ interactive: true }, async (token) => {
                if (chrome.runtime.lastError || !token) {
                    console.warn("[Travel Saver] Auth failed or missing Client ID. Falling back to Demo Mode.");
                    handleDemoLogin();
                    return;
                }

                // Fetch real user info from Google
                const res = await fetch(`https://www.googleapis.com/oauth2/v1/userinfo?alt=json&access_token=${token}`);
                const data = await res.json();

                const user = {
                    name: data.name,
                    avatar: data.picture,
                    email: data.email
                };

                await chrome.storage.local.set({ userData: user });
                showUserInfo(user);
                showToast(`Welcome back, ${user.name}!`);
            });
        } catch (err) {
            console.error("[Travel Saver] Identity error:", err);
            handleDemoLogin();
        }
    });
}

function showUserInfo(user) {
    btnLogin.style.display = "none";
    userInfo.style.display = "flex";
    userAvatar.src = user.avatar;
    userName.textContent = user.name;
}

function handleDemoLogin() {
    const demoUser = {
        name: "Travel Explorer",
        avatar: "https://www.gstatic.com/images/branding/product/2x/avatar_square_blue_120dp.png",
        email: "demo@travelsaver.ext"
    };
    chrome.storage.local.set({ userData: demoUser });
    showUserInfo(demoUser);
    showToast("Signed in as Travel Explorer (Demo Mode)");
}

// ============================================================
// YOUTUBE HELPERS
// ============================================================
function extractYouTubeId(url) {
    try {
        const u = new URL(url);
        if (u.hostname.includes("youtube.com")) return u.searchParams.get("v") || null;
        if (u.hostname === "youtu.be") return u.pathname.slice(1).split("?")[0] || null;
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
            const parts = (tab.title || "").split(" - ");
            btnSaveSong.dataset.channel = parts.length >= 2 ? parts.slice(1, -1).join(" - ") : "YouTube";
        }
    } catch { }
}

// ============================================================
// TABS
// ============================================================
function setupTabs() {
    document.querySelectorAll(".tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(p => p.classList.remove("active"));
            tab.classList.add("active");
            document.getElementById("panel" + cap(tab.dataset.tab)).classList.add("active");
            currentTab = tab.dataset.tab;
        });
    });
}

function cap(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// ============================================================
// SAVE HANDLERS
// ============================================================
function setupSaveHandlers() {
    // ---- Save YouTube song (local) ----
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
        await addLocalItem(item);
        renderSongs();
        showToast("🎵 Song saved!");
        document.getElementById("tabSongs").click();
    });

    // ---- Save current page (local) ----
    btnSavePage.addEventListener("click", async () => {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab || !tab.url || tab.url.startsWith("chrome://")) {
            showToast("⚠️ Can't save this page"); return;
        }
        const item = {
            id: Date.now().toString(),
            type: "page",
            url: tab.url,
            title: tab.title || tab.url,
            favicon: `https://www.google.com/s2/favicons?sz=64&domain=${new URL(tab.url).hostname}`,
            date: new Date().toISOString()
        };
        await addLocalItem(item);
        renderPages();
        showToast("✈️ Page saved!");
        document.getElementById("tabPages").click();
    });

    // ---- Save text note (API) ----
    btnSaveText.addEventListener("click", async () => {
        const content = textInput.value.trim();
        if (!content) { showToast("Type something first!"); return; }
        textInput.disabled = true;
        btnSaveText.disabled = true;
        showLoader();
        try {
            const saved = await postText(content);
            apiTexts.unshift({
                id: saved.id, text: content, content_type: "text/plain",
                size_bytes: saved.size_bytes || 0, model: saved.model || ""
            });
            textInput.value = "";
            renderTexts();
            updateCount();
            showToast("📝 Note saved!");
        } catch (e) {
            console.error(e);
            showToast("❌ Failed to save note (backend down?)");
        } finally {
            hideLoader();
            textInput.disabled = false;
            btnSaveText.disabled = false;
        }
    });

    textInput.addEventListener("keydown", e => {
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) btnSaveText.click();
    });
}

// ============================================================
// PHOTO UPLOAD (API)
// ============================================================
function setupPhotoUpload() {
    async function handleFiles(files) {
        showLoader();

        for (const file of files) {
            try {
                const saved = await postImage(file, file.name);
                // Optimistically add a local preview while the list refreshes
                const dataUrl = await fileToDataUrl(file);
                apiPhotos.unshift({
                    id: saved.id,
                    filename: file.name,
                    content_type: file.type,
                    size_bytes: file.size,
                    image_base64: dataUrl.split(",")[1]  // strip data:…;base64, prefix
                });
            } catch (e) {
                console.error("[Travel Saver] Image upload failed:", e);
                showToast("❌ Failed to upload image (backend down?)");
            }
        }

        hideLoader();

        renderPhotos();
        updateCount();
        showToast(`📸 ${files.length} photo${files.length > 1 ? "s" : ""} saved!`);
    }

    photoInput.addEventListener("change", async e => {
        const files = Array.from(e.target.files);
        if (files.length) await handleFiles(files);
        photoInput.value = "";
    });

    const area = document.getElementById("photoUploadArea");
    area.addEventListener("dragover", e => { e.preventDefault(); area.style.borderColor = "var(--accent)"; });
    area.addEventListener("dragleave", () => { area.style.borderColor = ""; });
    area.addEventListener("drop", async e => {
        e.preventDefault();
        area.style.borderColor = "";
        const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith("image/"));
        if (files.length) await handleFiles(files);
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

// ============================================================
// RENDERERS
// ============================================================
function renderAll() {
    renderPages();
    renderTexts();
    renderPhotos();
    renderSongs();
    updateCount();
}

function renderPages() {
    const pages = localItems.filter(i => i.type === "page");
    Array.from(pagesList.children).forEach(c => { if (c !== pagesEmpty) c.remove(); });
    pagesEmpty.style.display = pages.length === 0 ? "" : "none";
    pages.forEach(item => {
        const card = document.createElement("div");
        card.className = "page-card";
        card.innerHTML = `
      <img class="page-favicon" src="${esc(item.favicon)}" alt="" onerror="this.style.display='none'" />
      <div class="page-info">
        <a class="page-title" href="${esc(item.url)}" title="${esc(item.title)}">${esc(item.title)}</a>
        <span class="page-url">${esc(item.url)}</span>
        <span class="page-date">${formatDate(item.date)}</span>
      </div>
      <button class="btn-delete" title="Remove">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>`;
        card.querySelector(".btn-delete").addEventListener("click", e => {
            e.preventDefault(); removeLocalItem(item.id);
        });
        card.querySelector(".page-title").addEventListener("click", e => {
            e.preventDefault(); chrome.tabs.create({ url: item.url });
        });
        pagesList.appendChild(card);
    });
}

function renderTexts() {
    Array.from(textsList.children).forEach(c => { if (c !== textsEmpty) c.remove(); });
    textsEmpty.style.display = apiTexts.length === 0 ? "" : "none";
    apiTexts.forEach(item => {
        const card = document.createElement("div");
        card.className = "text-card";
        card.innerHTML = `
      <p class="text-content">${esc(item.text)}</p>
      <button class="btn-delete" title="Remove">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>`;
        card.querySelector(".btn-delete").addEventListener("click", async e => {
            e.preventDefault();
            try {
                await deleteApiItem("texts", item.id);
                apiTexts = apiTexts.filter(t => t.id !== item.id);
                renderTexts();
                updateCount();
                showToast("🗑️ Text deleted");
            } catch (err) {
                console.error("[Travel Saver] Failed to delete text:", err);
                showToast("❌ Failed to delete text");
            }
        });
        textsList.appendChild(card);
    });
}

function renderPhotos() {
    Array.from(photoGrid.children).forEach(c => { if (c !== photosEmpty) c.remove(); });
    photosEmpty.style.display = apiPhotos.length === 0 ? "" : "none";
    apiPhotos.forEach(item => {
        const src = item.image_base64
            ? `data:${item.content_type || "image/jpeg"};base64,${item.image_base64}`
            : "";
        const wrap = document.createElement("div");
        wrap.className = "photo-thumb-wrap";
        wrap.innerHTML = `
      <img class="photo-thumb" src="${src}" alt="${esc(item.filename)}" />
      <span class="photo-name">${esc(item.filename)}</span>
      <button class="btn-delete" title="Remove">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>`;
        wrap.querySelector(".btn-delete").addEventListener("click", async e => {
            e.preventDefault();
            try {
                await deleteApiItem("images", item.id);
                apiPhotos = apiPhotos.filter(p => p.id !== item.id);
                renderPhotos();
                updateCount();
                showToast("🗑️ Photo deleted");
            } catch (err) {
                console.error("[Travel Saver] Failed to delete photo:", err);
                showToast("❌ Failed to delete photo");
            }
        });
        wrap.querySelector(".photo-thumb").addEventListener("click", () => {
            if (!src) return;
            const w = window.open();
            w.document.write(`<img src="${src}" style="max-width:100%;height:auto;" />`);
        });
        photoGrid.appendChild(wrap);
    });
}

function renderSongs() {
    const songs = localItems.filter(i => i.type === "song");
    Array.from(songsList.children).forEach(c => { if (c !== songsEmpty) c.remove(); });
    songsEmpty.style.display = songs.length === 0 ? "" : "none";
    songs.forEach(item => {
        const card = document.createElement("div");
        card.className = "song-card";
        card.innerHTML = `
      <div class="song-thumb-wrap">
        <img class="song-thumb" src="${esc(item.thumbnail)}" alt="${esc(item.title)}"
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
            e.stopPropagation(); removeLocalItem(item.id);
        });
        card.addEventListener("click", () => chrome.tabs.create({ url: item.url }));
        songsList.appendChild(card);
    });
}

// ============================================================
// UTILS
// ============================================================
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
    return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
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
