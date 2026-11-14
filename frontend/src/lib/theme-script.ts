// Plain module (no "use client") so the server layout can inline it as a string.
export const THEME_STORAGE_KEY = "deep-agent:theme";

/**
 * Runs in <head> before first paint so a saved choice never flashes the wrong theme.
 * With no saved choice the page follows the system setting via CSS (prefers-color-scheme).
 */
export const THEME_BOOT_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t;}catch(e){}})();`;
