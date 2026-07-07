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
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.status(status).send(JSON.stringify(body));
}

module.exports = async function handler(req, res) {
  const origin = allowedOrigin(req);
  if (req.method === "OPTIONS") {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    return res.status(204).send("");
  }
  if (req.method !== "POST") {
    return send(res, 405, { ok: false, error: "method_not_allowed" }, origin);
  }

  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    return send(res, 500, { ok: false, error: "missing_github_token" }, origin);
  }

  const repo = process.env.GITHUB_REPOSITORY || DEFAULT_REPO;
  const workflow = process.env.GITHUB_WORKFLOW_FILE || DEFAULT_WORKFLOW;
  const ref = process.env.GITHUB_BRANCH || DEFAULT_BRANCH;
  const url = `https://api.github.com/repos/${repo}/actions/workflows/${workflow}/dispatches`;

  const gh = await fetch(url, {
    method: "POST",
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
      "User-Agent": "xdgk-pricewatch-backend",
      "X-GitHub-Api-Version": "2022-11-28"
    },
    body: JSON.stringify({ ref })
  });

  if (!gh.ok) {
    const detail = await gh.text();
    return send(res, gh.status, { ok: false, error: "github_dispatch_failed", detail }, origin);
  }

  return send(res, 202, {
    ok: true,
    message: "Da gui yeu cau cao gia. Doi GitHub Actions chay xong roi tai lai dashboard.",
    actionsUrl: `https://github.com/${repo}/actions/workflows/${workflow}`
  }, origin);
};
