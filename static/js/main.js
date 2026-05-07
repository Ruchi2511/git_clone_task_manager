// ─── Flash auto-dismiss ───────────────────
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
      el.style.transition = "opacity 0.35s ease, transform 0.35s ease";
      el.style.opacity = "0";
      el.style.transform = "translateY(-6px)";
      setTimeout(() => el.remove(), 380);
    }, 4000);
  });

  // ─── Sidebar mobile toggle ───────────────
  const sidebar = document.querySelector(".sidebar");
  const overlay = document.getElementById("sidebar-overlay");
  const hamburger = document.getElementById("sidebar-toggle");

  if (hamburger && sidebar) {
    hamburger.addEventListener("click", () => {
      sidebar.classList.toggle("open");
      overlay && overlay.classList.toggle("active");
    });
  }

  if (overlay) {
    overlay.addEventListener("click", () => {
      sidebar && sidebar.classList.remove("open");
      overlay.classList.remove("active");
    });
  }

  // ─── Active nav item ─────────────────────
  const path = window.location.pathname;
  document.querySelectorAll(".nav-item").forEach((link) => {
    const href = link.getAttribute("href");
    if (href && path.startsWith(href) && href !== "/") {
      link.classList.add("active");
    } else if (href === "/" && path === "/") {
      link.classList.add("active");
    }
  });

  // Mark dashboard active when on root
  if (path === "/dashboard" || path === "/") {
    document.querySelectorAll('[data-nav="dashboard"]').forEach(el => el.classList.add("active"));
  }
});

// ─── Session verification ────────────────
async function verifyActiveSession() {
  if (document.body?.dataset?.protected !== "true") return;
  try {
    const res = await fetch("/auth/session-check", {
      method: "GET",
      cache: "no-store",
      credentials: "same-origin",
      headers: { "Cache-Control": "no-store" },
    });
    const data = await res.json();
    if (!data.authenticated) window.location.replace("/login");
  } catch {
    window.location.replace("/login");
  }
}

window.addEventListener("pageshow", (e) => {
  if (e.persisted || document.body?.dataset?.protected === "true") verifyActiveSession();
});

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") verifyActiveSession();
});
