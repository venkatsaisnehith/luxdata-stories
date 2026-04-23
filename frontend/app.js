/* LuxData Stories — Dashboard Controller */

(function () {
    "use strict";

    const API = {
        stories: "/api/stories",
        topics: "/api/stories/topics",
        stats: "/api/stats",
        refresh: "/api/refresh",
    };

    const grid = document.getElementById("stories-grid");
    const emptyState = document.getElementById("empty-state");
    const errorState = document.getElementById("error-state");
    const pillEl = document.getElementById("story-count-pill");
    const lastUpdatedEl = document.getElementById("last-updated");
    const refreshBtn = document.getElementById("refresh-btn");

    let activeTopic = "all";

    /* ===== Init ===== */
    document.addEventListener("DOMContentLoaded", init);

    async function init() {
        showSkeletons();
        attachFilterListeners();
        attachRefreshListener();
        await Promise.all([loadStories(), loadStats(), loadTopicCounts()]);
        setInterval(silentRefresh, 30 * 60 * 1000);
    }

    /* ===== Data Fetching ===== */
    async function fetchJSON(url, opts) {
        try {
            const res = await fetch(url, opts);
            if (!res.ok) throw new Error(res.statusText);
            return await res.json();
        } catch {
            return null;
        }
    }

    async function loadStories(topic) {
        const t = topic || activeTopic;
        let url = API.stories + "?limit=20";
        if (t && t !== "all") url += "&topic=" + encodeURIComponent(t);

        const data = await fetchJSON(url);
        if (data === null) {
            showError();
            return;
        }
        renderStories(data);
    }

    async function loadStats() {
        const data = await fetchJSON(API.stats);
        if (!data) return;

        setText("#stat-stories .stat-value", data.total_stories || 0);
        setText("#stat-datasets .stat-value", data.datasets_monitored || 0);
        setText("#stat-topics .stat-value", data.topics_covered || 0);
        pillEl.textContent = (data.total_stories || 0) + " stories";

        if (data.last_updated) {
            lastUpdatedEl.textContent = "Last updated: " + relativeTime(data.last_updated);
        }
    }

    async function loadTopicCounts() {
        const data = await fetchJSON(API.topics);
        if (!data) return;

        let total = 0;
        const counts = {};
        data.forEach(function (item) {
            counts[item.topic] = item.count;
            total += item.count;
        });

        setBadge("badge-all", total);
        ["housing", "employment", "transport", "environment", "economy", "health"].forEach(function (t) {
            setBadge("badge-" + t, counts[t] || 0);
        });
    }

    async function silentRefresh() {
        await Promise.all([loadStories(), loadStats(), loadTopicCounts()]);
    }

    /* ===== Rendering ===== */
    function renderStories(stories) {
        hideError();
        grid.innerHTML = "";

        if (!stories || stories.length === 0) {
            grid.style.display = "none";
            emptyState.style.display = "block";
            return;
        }

        emptyState.style.display = "none";
        grid.style.display = "grid";

        stories.forEach(function (story, idx) {
            var card = buildCard(story, idx);
            grid.appendChild(card);
        });
    }

    function buildCard(story, idx) {
        var card = el("div", "story-card");
        card.style.animationDelay = (idx * 0.05) + "s";

        var topic = story.topic || "economy";
        var date = story.date || "";
        var body = story.body || "";
        var isLong = body.length > 150;

        // Header
        var header = el("div", "card-header");
        var badge = el("span", "topic-badge " + topic);
        badge.textContent = topic;
        var dateEl = el("span", "card-date");
        dateEl.textContent = date ? relativeTime(date) : "";
        header.appendChild(badge);
        header.appendChild(dateEl);

        // Title
        var title = el("h2", "card-title");
        title.textContent = story.title || "Untitled";

        // Body
        var bodyEl = el("p", "card-body" + (isLong ? " collapsed" : ""));
        bodyEl.textContent = body;

        // Read more
        var readMoreEl = null;
        if (isLong) {
            readMoreEl = el("button", "read-more-btn");
            readMoreEl.textContent = "Read more";
            readMoreEl.addEventListener("click", function () {
                var collapsed = bodyEl.classList.toggle("collapsed");
                readMoreEl.textContent = collapsed ? "Read more" : "Read less";
            });
        }

        // Footer
        var footer = el("div", "card-footer");
        if (story.source_url) {
            var link = document.createElement("a");
            link.className = "source-link";
            link.href = story.source_url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = "View Source Data \u2192";
            footer.appendChild(link);
        }

        card.appendChild(header);
        card.appendChild(title);
        card.appendChild(bodyEl);
        if (readMoreEl) card.appendChild(readMoreEl);
        card.appendChild(footer);

        return card;
    }

    function showSkeletons() {
        grid.innerHTML = "";
        grid.style.display = "grid";
        emptyState.style.display = "none";
        for (var i = 0; i < 4; i++) {
            var sk = el("div", "skeleton-card");
            sk.appendChild(skLine("short"));
            sk.appendChild(skLine("medium"));
            sk.appendChild(skLine("long"));
            sk.appendChild(skLine("long"));
            grid.appendChild(sk);
        }
    }

    function skLine(cls) {
        return el("div", "skeleton-line " + cls);
    }

    function showError() {
        grid.style.display = "none";
        emptyState.style.display = "none";
        errorState.style.display = "block";
    }

    function hideError() {
        errorState.style.display = "none";
    }

    /* ===== Filters ===== */
    function attachFilterListeners() {
        document.querySelectorAll(".filter-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                document.querySelectorAll(".filter-btn").forEach(function (b) { b.classList.remove("active"); });
                btn.classList.add("active");
                activeTopic = btn.dataset.topic;
                showSkeletons();
                loadStories(activeTopic);
            });
        });
    }

    /* ===== Refresh ===== */
    function attachRefreshListener() {
        refreshBtn.addEventListener("click", async function () {
            refreshBtn.classList.add("refreshing");
            refreshBtn.querySelector(".refresh-icon").textContent = "\u21BB";
            var span = refreshBtn.childNodes[refreshBtn.childNodes.length - 1];
            if (span.nodeType === 3) span.textContent = " Refreshing\u2026";

            await fetchJSON(API.refresh, { method: "POST" });
            setTimeout(async function () {
                await silentRefresh();
                refreshBtn.classList.remove("refreshing");
                if (span.nodeType === 3) span.textContent = " Refresh Now";
            }, 5000);
        });
    }

    /* ===== Helpers ===== */
    function el(tag, cls) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        return e;
    }

    function setText(selector, val) {
        var e = document.querySelector(selector);
        if (e) e.textContent = val;
    }

    function setBadge(id, count) {
        var e = document.getElementById(id);
        if (e) e.textContent = count;
    }

    function relativeTime(isoStr) {
        try {
            var d = new Date(isoStr);
            var now = new Date();
            var diffMs = now - d;
            var diffSec = Math.floor(diffMs / 1000);
            var diffMin = Math.floor(diffSec / 60);
            var diffHr = Math.floor(diffMin / 60);
            var diffDay = Math.floor(diffHr / 24);

            if (diffSec < 60) return "Just now";
            if (diffMin < 60) return diffMin + " min ago";
            if (diffHr < 24) return diffHr + " hour" + (diffHr > 1 ? "s" : "") + " ago";
            if (diffDay === 1) return "Yesterday";
            if (diffDay < 30) return diffDay + " days ago";
            return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
        } catch {
            return isoStr;
        }
    }
})();
