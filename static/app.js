const decisionForm = document.getElementById("decision-form");
const tabButtons = document.querySelectorAll(".tab-btn");
const tabPanels = document.querySelectorAll(".tab-panel");

const linkedinBtn = document.getElementById("connect-linkedin-btn");
const singpassBtn = document.getElementById("connect-singpass-btn");
const linkedinLoading = document.getElementById("linkedin-loading");
const singpassLoading = document.getElementById("singpass-loading");

const linkedinResult = document.getElementById("linkedin-result");
const singpassResult = document.getElementById("singpass-result");
const ownResult = document.getElementById("own-result");
const simResult = document.getElementById("sim-result");
const jobsResult = document.getElementById("jobs-result");
const swarmResult = document.getElementById("swarm-result");

const runSimBtn = document.getElementById("run-sim-btn");
const runJobsBtn = document.getElementById("run-jobs-btn");
const runSwarmBtn = document.getElementById("run-swarm-btn");

function formToObject(form) {
  const data = new FormData(form);
  return Object.fromEntries(data.entries());
}

function setField(name, value) {
  const field = decisionForm.querySelector(`[name="${name}"]`);
  if (!field || value === undefined || value === null) return;
  field.value = value;
}

function showBlock(target, html) {
  target.classList.remove("hidden");
  target.innerHTML = html;
}

function traceList(trace) {
  if (!trace || !trace.length) return "No trace.";
  return `<ul>${trace.map((t) => `<li><strong>${t.agent}</strong>: ${t.step}</li>`).join("")}</ul>`;
}

function list(items) {
  if (!items || !items.length) return "None";
  return `<ul>${items.map((i) => `<li>${i}</li>`).join("")}</ul>`;
}

function switchTab(tabId) {
  tabButtons.forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tabId));
  tabPanels.forEach((panel) => panel.classList.toggle("active", panel.id === tabId));
}

tabButtons.forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

linkedinBtn.addEventListener("click", async () => {
  linkedinLoading.classList.remove("hidden");
  linkedinBtn.disabled = true;
  try {
    const payload = {
      profile_url: decisionForm.querySelector('[name="profile_url"]').value,
    };
    const response = await fetch("/api/connect/linkedin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(JSON.stringify(result));

    setField("top_skills", result.autofill.top_skills);
    setField("years_experience", result.autofill.years_experience);
    setField("current_role", result.autofill.current_role);

    const jobs = (result.profile.jobs || [])
      .map((j) => `<li>${j.title} at ${j.company} (${j.years}y)</li>`)
      .join("");
    const education = (result.profile.education || [])
      .map((e) => `<li>${e.degree}, ${e.school}</li>`)
      .join("");

    showBlock(
      linkedinResult,
      `<h4>LinkedIn Pull</h4>
       <p><strong>${result.profile.name}</strong></p>
       <p><strong>Jobs:</strong></p><ul>${jobs}</ul>
       <p><strong>Education:</strong></p><ul>${education}</ul>
       <p><strong>Skill Reasoner:</strong> ${result.skill_reasoning.narrative}</p>
       <p><strong>Inferred Skills:</strong> ${result.skill_reasoning.inferred_skills.join(", ")}</p>
       <p><strong>Process:</strong></p>${traceList(result.trace)}`
    );
  } catch (error) {
    showBlock(linkedinResult, `<p>LinkedIn connection failed: ${error.message}</p>`);
  } finally {
    linkedinLoading.classList.add("hidden");
    linkedinBtn.disabled = false;
  }
});

singpassBtn.addEventListener("click", async () => {
  singpassLoading.classList.remove("hidden");
  singpassBtn.disabled = true;
  try {
    const response = await fetch("/api/connect/singpass", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(JSON.stringify(result));

    Object.entries(result.autofill || {}).forEach(([name, value]) => setField(name, value));

    showBlock(
      singpassResult,
      `<h4>Singpass Pull</h4>
       <p>${(result.notes || []).join(" ")}</p>
       <p><strong>Fill manually:</strong> ${(result.required_user_inputs || []).join(", ")}</p>
       <p><strong>Process:</strong></p>${traceList(result.trace)}`
    );
  } catch (error) {
    showBlock(singpassResult, `<p>Singpass connection failed: ${error.message}</p>`);
  } finally {
    singpassLoading.classList.add("hidden");
    singpassBtn.disabled = false;
  }
});

decisionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = formToObject(decisionForm);
  const response = await fetch("/api/self/process", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams(payload),
  });
  const result = await response.json();
  if (!response.ok) {
    showBlock(ownResult, `<p>Error: ${JSON.stringify(result)}</p>`);
    return;
  }

  showBlock(
    ownResult,
    `<h4>Own-Agent Opinion</h4>
     <p><strong>Score:</strong> ${result.aggregate_score_0_to_100}/100</p>
     <p><strong>Recommendation:</strong> ${result.recommendation}</p>
     <p><strong>Your simulated opinion:</strong> ${result.self_simulated_opinion}</p>
     <p><strong>Rationale:</strong></p>${list(result.rationale)}
     <p><strong>Process:</strong></p>${traceList(result.trace)}`
  );
});

runSimBtn.addEventListener("click", async () => {
  const payload = {
    ...formToObject(decisionForm),
    external_linkedin_urls: document.getElementById("external_linkedin_urls").value,
  };
  const response = await fetch("/api/simulated/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok) {
    showBlock(simResult, `<p>Error: ${JSON.stringify(result)}</p>`);
    return;
  }

  const opinions = result.opinions?.length
    ? `<ul>${result.opinions
        .map(
          (o) =>
            `<li><strong>${o.advisor_name}</strong> (${o.stance}): ${o.message}<br/>skills: ${o.top_skills.join(
              ", "
            )}</li>`
        )
        .join("")}</ul>`
    : "No profiles imported.";

  showBlock(
    simResult,
    `<h4>Simulated Opinions</h4>
     <p><strong>Consensus:</strong> ${result.consensus}</p>
     ${opinions}
     <p><strong>Process:</strong></p>${traceList(result.trace)}`
  );
});

runJobsBtn.addEventListener("click", async () => {
  const payload = {
    target_role: document.getElementById("target_role").value,
    target_location: document.getElementById("target_location").value,
  };
  const response = await fetch("/api/jobs/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  const jobs = result.jobs?.length
    ? `<ul>${result.jobs
        .map((j) => `<li>${j.title} - ${j.company} (${j.location}) | ${j.salary_range}</li>`)
        .join("")}</ul>`
    : "No jobs found.";

  showBlock(
    jobsResult,
    `<h4>Jobs Agent Result</h4>
     <p><strong>Market signal:</strong> ${result.market_signal_score_0_to_100}/100</p>
     <p><strong>Opinion:</strong> ${result.opinion}</p>
     ${jobs}
     <p><strong>Process:</strong></p>${traceList(result.trace)}`
  );
});

runSwarmBtn.addEventListener("click", async () => {
  const payload = {
    ...formToObject(decisionForm),
    external_linkedin_urls: document.getElementById("external_linkedin_urls").value,
    target_role: document.getElementById("target_role").value,
    target_location: document.getElementById("target_location").value,
  };
  const response = await fetch("/api/swarm/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok) {
    showBlock(swarmResult, `<p>Error: ${JSON.stringify(result)}</p>`);
    return;
  }

  showBlock(
    swarmResult,
    `<h4>Agentic Swarm Final</h4>
     <p><strong>Final opinion:</strong> ${result.swarm_final_opinion}</p>
     <p><strong>Self score:</strong> ${result.self_decision.aggregate_score_0_to_100}/100</p>
     <p><strong>Peer consensus:</strong> ${result.peer_simulation.consensus}</p>
     <p><strong>Job market score:</strong> ${result.job_market.market_signal_score_0_to_100}/100</p>
     <p><strong>Swarm process:</strong></p>${traceList(result.trace)}`
  );

  switchTab("tab-swarm");
});
