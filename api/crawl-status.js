const DEFAULT_REPO = "Quynhlong0222/xdgk-pricewatch";
const DEFAULT_WORKFLOW = "cao-gia.yml";
const DEFAULT_BRANCH = "main";

function allowedOrigin(req) {
  const origin = req.headers.origin || "";
  const allowed = (process.env.ALLOWED_ORIGIN || "https://quynhlong0222.github.io")
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);
  if (allowed.includes("*")) return "*";
  return allowed.includes(origin) ? origin : allowed[0] || "*";
}

function send(res, status, body, origin) {
  res.setHeader("Access-Control-Allow-Origin", origin);
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.status(status).send(JSON.stringify(body));
}

module.exports = async function handler(req, res) {
  const origin = allowedOrigin(req);
  if (req.method === "OPTIONS") {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    return res.status(204).send("");
  }
  if (req.method !== "GET") {
    return send(res, 405, { ok: false, error: "method_not_allowed" }, origin);
  }

  const repo = process.env.GITHUB_REPOSITORY || DEFAULT_REPO;
  const workflow = process.env.GITHUB_WORKFLOW_FILE || DEFAULT_WORKFLOW;
  const branch = process.env.GITHUB_BRANCH || DEFAULT_BRANCH;
  const url = `https://api.github.com/repos/${repo}/actions/workflows/${workflow}/runs?branch=${encodeURIComponent(branch)}&per_page=1`;
  const headers = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "xdgk-pricewatch-backend",
    "X-GitHub-Api-Version": "2022-11-28"
  };
  if (process.env.GITHUB_TOKEN) headers.Authorization = `Bearer ${process.env.GITHUB_TOKEN}`;

  const gh = await fetch(url, { headers });
  if (!gh.ok) {
    const detail = await gh.text();
    return send(res, gh.status, { ok: false, error: "github_status_failed", detail }, origin);
  }

  const data = await gh.json();
  const run = data.workflow_runs && data.workflow_runs[0];
  return send(res, 200, {
    ok: true,
    run: run ? {
      id: run.id,
      status: run.status,
      conclusion: run.conclusion,
      created_at: run.created_at,
      updated_at: run.updated_at,
      html_url: run.html_url
    } : null
  }, origin);
};
