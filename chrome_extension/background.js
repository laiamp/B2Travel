// background.js — Service Worker for Travel Saver
const API_BASE = "http://127.0.0.1:8000";

chrome.runtime.onInstalled.addListener(() => {
    // Context menu for selected text
    chrome.contextMenus.create({
        id: "save-text",
        title: "💬 Save quote to B2Travel",
        contexts: ["selection"]
    });

    // Context menu for images
    chrome.contextMenus.create({
        id: "save-image",
        title: "🏞️️ Save image to B2Travel",
        contexts: ["image"]
    });

    // Context menu for links/page
    chrome.contextMenus.create({
        id: "save-page",
        title: "🌐️ Save page to B2Travel",
        contexts: ["page", "link"]
    });

    // Context menu for YouTube links
    chrome.contextMenus.create({
        id: "save-song",
        title: "🎵 Save as song to B2Travel",
        contexts: ["link"]
    });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
    if (info.menuItemId === "save-text") {
        // POST text to backend API for embedding + storage
        try {
            const form = new FormData();
            form.append("text", info.selectionText);
            const res = await fetch(`${API_BASE}/ingest/text`, { method: "POST", body: form });
            if (!res.ok) console.warn("[Travel Saver] Text ingest failed:", res.status);
        } catch (e) {
            console.warn("[Travel Saver] Backend unreachable (text):", e.message);
        }
        showNotification("Text saved to Travel Board!");
    }

    if (info.menuItemId === "save-image") {
        try {
            const response = await fetch(info.srcUrl);
            const blob = await response.blob();
            const dataUrl = await blobToDataUrl(blob);
            const name = info.srcUrl.split("/").pop().split("?")[0] || "image.jpg";
            const item = {
                id: Date.now().toString(),
                type: "photo",
                dataUrl,
                name,
                sourceUrl: tab.url,
                date: new Date().toISOString()
            };
            await saveItem(item);
            ingestImageBlob(blob, name); // fire-and-forget
            showNotification("Image saved to Travel Board!");
        } catch (e) {
            console.error("Failed to save image:", e);
        }
    }

    if (info.menuItemId === "save-song") {
        const url = info.linkUrl;
        const videoId = extractYouTubeId(url);
        if (!videoId) {
            // Not a YouTube link — ignore silently
            return;
        }
        const item = {
            id: Date.now().toString(),
            type: "song",
            videoId,
            title: url, // title unknown from context menu; user can rename later
            channel: "YouTube",
            thumbnail: `https://img.youtube.com/vi/${videoId}/mqdefault.jpg`,
            url,
            date: new Date().toISOString()
        };
        await saveItem(item);
        showNotification("🎵 Song saved!");
    }

    if (info.menuItemId === "save-page") {
        const url = info.linkUrl || tab.url;
        const title = info.linkUrl ? info.linkUrl : tab.title;
        const item = {
            id: Date.now().toString(),
            type: "page",
            url,
            title,
            favicon: `https://www.google.com/s2/favicons?sz=64&domain=${new URL(url).hostname}`,
            date: new Date().toISOString()
        };
        await saveItem(item);
        showNotification("Page saved to Travel Board!");
    }
});

async function saveItem(item) {
    const result = await chrome.storage.local.get("travelItems");
    const items = result.travelItems || [];
    items.unshift(item);
    await chrome.storage.local.set({ travelItems: items });
}

function extractYouTubeId(url) {
    try {
        const u = new URL(url);
        if (u.hostname.includes("youtube.com")) return u.searchParams.get("v") || null;
        if (u.hostname === "youtu.be") return u.pathname.slice(1).split("?")[0] || null;
    } catch { }
    return null;
}

function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

function showNotification(message) {
    chrome.action.setBadgeText({ text: "✓" });
    chrome.action.setBadgeBackgroundColor({ color: "#00e5cc" });
    setTimeout(() => chrome.action.setBadgeText({ text: "" }), 2000);
}

// ---- Backend ingestion ----
async function ingestImageBlob(blob, filename) {
    try {
        const form = new FormData();
        form.append("image", blob, filename || "image.jpg");
        const res = await fetch(`${API_BASE}/ingest/image`, { method: "POST", body: form });
        if (!res.ok) console.warn("[Travel Saver] Ingest failed:", res.status);
        else console.log("[Travel Saver] Ingested:", filename);
    } catch (err) {
        console.warn("[Travel Saver] Backend unreachable, skipping ingest:", err.message);
    }
}
