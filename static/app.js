const decisionForm = document.getElementById("decision-form");

const linkedinBtn = document.getElementById("connect-linkedin-btn");
const singpassBtn = document.getElementById("connect-singpass-btn");
const linkedinLoading = document.getElementById("linkedin-loading");
const singpassLoading = document.getElementById("singpass-loading");

const linkedinResult = document.getElementById("linkedin-result");
const singpassResult = document.getElementById("singpass-result");
const ownResult = document.getElementById("own-result");
const simResult = document.getElementById("sim-result");
const jobsResult = document.getElementById("jobs-result");
const newsResult = document.getElementById("news-result");
const swarmResult = document.getElementById("swarm-result");

const runSimBtn = document.getElementById("run-sim-btn");
const runJobsBtn = document.getElementById("run-jobs-btn");
const runNewsBtn = document.getElementById("run-news-btn");
const runSwarmBtn = document.getElementById("run-swarm-btn");

const profileUrlInput = document.getElementById("profile_url_input");
const nameSuggestionBubble = document.getElementById("name-suggestion-bubble");

// Extract LinkedIn username from URL and show in bubble
function updateNameSuggestion() {
  const url = profileUrlInput.value.trim();
  const match = url.match(/linkedin\.com\/in\/([^\/\?]+)/i);
  
  if (match && match[1]) {
    const username = match[1];
    nameSuggestionBubble.textContent = username;
    nameSuggestionBubble.classList.remove("hidden");
  } else {
    nameSuggestionBubble.classList.add("hidden");
  }
}

// Update suggestion bubble on input
profileUrlInput.addEventListener("input", updateNameSuggestion);

// Initialize on page load
updateNameSuggestion();

// Handle career goal suggestion clicks
const careerGoalInput = document.getElementById("career_goal_input");
const careerSuggestionChips = document.querySelectorAll(".suggestion-chip:not(.linkedin-url-chip)");

careerSuggestionChips.forEach(chip => {
  chip.addEventListener("click", (e) => {
    const goal = e.target.getAttribute("data-goal");
    if (careerGoalInput && goal) {
      careerGoalInput.value = goal;
      careerGoalInput.focus();
      
      // Add visual feedback
      e.target.style.background = "rgba(0, 211, 167, 0.3)";
      setTimeout(() => {
        e.target.style.background = "";
      }, 300);
    }
  });
});

// Handle LinkedIn URL suggestion clicks
const linkedinUrlTextarea = document.getElementById("external_linkedin_urls");
const linkedinUrlChips = document.querySelectorAll(".linkedin-url-chip");

linkedinUrlChips.forEach(chip => {
  chip.addEventListener("click", (e) => {
    const url = e.target.getAttribute("data-url");
    if (linkedinUrlTextarea && url) {
      // Get current value
      const currentValue = linkedinUrlTextarea.value.trim();
      
      // Check if URL already exists
      if (currentValue.includes(url)) {
        // URL already added, flash feedback
        e.target.style.background = "rgba(255, 179, 71, 0.3)";
        setTimeout(() => {
          e.target.style.background = "";
        }, 300);
        return;
      }
      
      // Add URL to textarea (append with newline if not empty)
      if (currentValue) {
        linkedinUrlTextarea.value = currentValue + "\n" + url;
      } else {
        linkedinUrlTextarea.value = url;
      }
      
      linkedinUrlTextarea.focus();
      
      // Add visual feedback
      e.target.style.background = "rgba(138, 244, 220, 0.3)";
      setTimeout(() => {
        e.target.style.background = "";
      }, 300);
    }
  });
});

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

linkedinBtn.addEventListener("click", async () => {
  linkedinLoading.classList.remove("hidden");
  linkedinBtn.disabled = true;
  try {
    const payload = { profile_url: decisionForm.querySelector('[name="profile_url"]').value };
    const response = await fetch("/api/connect/linkedin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(JSON.stringify(result));

    // Populate "Your Details" fields from LinkedIn data (except career goal)
    if (result.profile.name) {
      setField("name", result.profile.name);
    }
    
    // Populate from autofill
    if (result.autofill) {
      setField("current_role", result.autofill.current_role);
      setField("years_experience", result.autofill.years_experience);
      setField("top_skills", result.autofill.top_skills);
    }
    
    // Populate location if available (default to Singapore if not)
    if (result.profile.location) {
      setField("location", result.profile.location);
    } else {
      setField("location", "Singapore");
    }
    
    // Populate age if available (default to 31 if not)
    if (result.profile.age) {
      setField("age", result.profile.age);
    } else {
      setField("age", "31");
    }
    
    // Set default risk tolerance to medium if not already set
    const riskField = decisionForm.querySelector('[name="risk_tolerance"]');
    if (riskField && !riskField.value) {
      setField("risk_tolerance", "medium");
    }
    
    // Set default LinkedIn details
    const endorsementsField = decisionForm.querySelector('[name="endorsements_strength"]');
    if (endorsementsField && !endorsementsField.value) {
      setField("endorsements_strength", "moderate");
    }
    
    const networkField = decisionForm.querySelector('[name="network_reach"]');
    if (networkField && !networkField.value) {
      setField("network_reach", "medium");
    }
    
    const postsField = decisionForm.querySelector('[name="recent_relevant_posts"]');
    if (postsField && !postsField.value) {
      setField("recent_relevant_posts", "4");
    }
    
    // Auto-populate Jobs + News section based on current role and location
    const targetRoleField = document.getElementById("target_role");
    const targetLocationField = document.getElementById("target_location");
    const newsTopicField = document.getElementById("news_topic");
    const horizonField = document.getElementById("horizon_months");
    
    if (targetRoleField && !targetRoleField.value && result.autofill.current_role) {
      targetRoleField.value = result.autofill.current_role;
    }
    
    if (targetLocationField && !targetLocationField.value && result.profile.location) {
      targetLocationField.value = result.profile.location;
    } else if (targetLocationField && !targetLocationField.value) {
      targetLocationField.value = "Singapore";
    }
    
    if (newsTopicField && !newsTopicField.value && result.autofill.current_role) {
      // Extract key terms from current role for news topic
      newsTopicField.value = result.autofill.current_role.split(" ").slice(0, 2).join(" ");
    }
    
    if (horizonField && !horizonField.value) {
      horizonField.value = "6";
    }

    const jobs = (result.profile.jobs || [])
      .map((j) => `<li>${j.title} at ${j.company} (${j.years}y)</li>`)
      .join("");
    const education = (result.profile.education || [])
      .map((e) => `<li>${e.degree}, ${e.school}</li>`)
      .join("");

    showBlock(
      linkedinResult,
      `<h4>✅ LinkedIn Profile Connected</h4>
       <p><strong>${result.profile.name}</strong></p>
       <p><strong>Jobs:</strong></p><ul>${jobs}</ul>
       <p><strong>Education:</strong></p><ul>${education}</ul>
       <p><strong>Skill Reasoner:</strong> ${result.skill_reasoning.narrative}</p>
       <p><strong>Inferred Skills:</strong> ${result.skill_reasoning.inferred_skills.join(", ")}</p>
       <p><strong>Process:</strong></p>${traceList(result.trace)}`
    );
    
    // Show career goal suggestions after successful connection
    const careerSuggestions = document.getElementById('career-suggestions');
    if (careerSuggestions) {
      careerSuggestions.classList.remove('hidden');
      // Smooth animation
      setTimeout(() => {
        careerSuggestions.style.opacity = '1';
      }, 100);
    }
    
    // Scroll to "Your Details" section smoothly
    const yourDetailsSection = document.querySelector('h3');
    if (yourDetailsSection) {
      yourDetailsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  } catch (error) {
    showBlock(linkedinResult, `<p>❌ LinkedIn connection failed: ${error.message}</p>`);
  } finally {
    linkedinLoading.classList.add("hidden");
    linkedinBtn.disabled = false;
  }
});

singpassBtn.addEventListener("click", async () => {
  singpassLoading.classList.remove("hidden");
  singpassBtn.disabled = true;
  try {
    // Collect profile data from the form
    const profileData = {
      name: decisionForm.querySelector('[name="name"]')?.value || "Professional",
      current_role: decisionForm.querySelector('[name="current_role"]')?.value || "Product Manager",
      years_experience: parseFloat(decisionForm.querySelector('[name="years_experience"]')?.value) || 8,
      location: decisionForm.querySelector('[name="location"]')?.value || "Singapore",
      age: parseInt(decisionForm.querySelector('[name="age"]')?.value) || 31,
    };
    
    const response = await fetch("/api/connect/singpass", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(profileData),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(JSON.stringify(result));

    // Populate fields from autofill or set sensible defaults
    Object.entries(result.autofill || {}).forEach(([name, value]) => setField(name, value));
    
    // Set defaults for family fields if not already set
    const dependentsField = decisionForm.querySelector('[name="dependents_count"]');
    if (dependentsField && !dependentsField.value) {
      setField("dependents_count", "1");
    }
    
    const partnerIncomeField = decisionForm.querySelector('[name="partner_income_stable"]');
    if (partnerIncomeField && !partnerIncomeField.value) {
      setField("partner_income_stable", "true");
    }
    
    const familySupportField = decisionForm.querySelector('[name="family_support_level"]');
    if (familySupportField && !familySupportField.value) {
      setField("family_support_level", "medium");
    }
    
    const insuranceField = decisionForm.querySelector('[name="health_insurance_if_quit"]');
    if (insuranceField && !insuranceField.value) {
      setField("health_insurance_if_quit", "true");
    }

    showBlock(
      singpassResult,
      `<h4>✅ Singpass Connected</h4>
       <p>${(result.notes || []).join(" ")}</p>
       <p><strong>Fill manually:</strong> ${(result.required_user_inputs || []).join(", ")}</p>
       <p><strong>Process:</strong></p>${traceList(result.trace)}`
    );
  } catch (error) {
    showBlock(singpassResult, `<p>❌ Singpass connection failed: ${error.message}</p>`);
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

runNewsBtn.addEventListener("click", async () => {
  const payload = {
    news_topic: document.getElementById("news_topic").value,
    target_location: document.getElementById("target_location").value,
    horizon_months: document.getElementById("horizon_months").value,
  };
  const response = await fetch("/api/news/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  const articles = result.articles?.length
    ? `<ul>${result.articles
        .map((a) => `<li>${a.title}${a.url ? ` — <a href="${a.url}" target="_blank">link</a>` : ""}<br/>${a.snippet}</li>`)
        .join("")}</ul>`
    : "No articles found.";
  showBlock(
    newsResult,
    `<h4>News Agent</h4>
     <p><strong>Outlook:</strong> ${result.outlook}</p>
     ${articles}
     <p><strong>Process:</strong></p>${traceList(result.trace)}`
  );
});

runSwarmBtn.addEventListener("click", async () => {
  const payload = {
    ...formToObject(decisionForm),
    external_linkedin_urls: document.getElementById("external_linkedin_urls").value,
    target_role: document.getElementById("target_role").value,
    target_location: document.getElementById("target_location").value,
    news_topic: document.getElementById("news_topic").value,
    horizon_months: document.getElementById("horizon_months").value,
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
     <p><strong>News outlook:</strong> ${result.news.outlook}</p>
     <p><strong>Swarm process:</strong></p>${traceList(result.trace)}`
  );
});
