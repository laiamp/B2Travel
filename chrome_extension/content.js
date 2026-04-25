// content.js — Content script for Travel Saver
// Listens for messages from the extension popup or background

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "GET_SELECTION") {
        const selected = window.getSelection().toString().trim();
        sendResponse({ text: selected });
    }
    if (message.type === "GET_PAGE_META") {
        const ogImage = document.querySelector('meta[property="og:image"]');
        sendResponse({
            title: document.title,
            url: window.location.href,
            description: document.querySelector('meta[name="description"]')?.content || "",
            image: ogImage?.content || null
        });
    }
    return true; // keep channel open for async
});
