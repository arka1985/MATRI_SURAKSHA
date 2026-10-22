/**
 * MatriSuraksha Extension - Client-side Triage Assistant
 */

document.addEventListener("DOMContentLoaded", () => {
  const fields = ["ext-sbp", "ext-dbp", "ext-hb", "ext-pulse", "ext-fhr", "ext-ga", "ext-rom"];

  fields.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", calculateTriage);
      el.addEventListener("change", calculateTriage);
    }
  });

  calculateTriage();
});

function calculateTriage() {
  const sbp = parseFloat(document.getElementById("ext-sbp").value) || 120;
  const dbp = parseFloat(document.getElementById("ext-dbp").value) || 80;
  const hb = parseFloat(document.getElementById("ext-hb").value) || 11.0;
  const pulse = parseFloat(document.getElementById("ext-pulse").value) || 78;
  const fhr = parseFloat(document.getElementById("ext-fhr").value) || 140;
  const ga = parseFloat(document.getElementById("ext-ga").value) || 39;
  const rom = document.getElementById("ext-rom").checked;

  const card = document.getElementById("ai-decision-card");
  const badge = document.getElementById("ai-badge");
  const headline = document.getElementById("ai-headline");
  const rationale = document.getElementById("ai-rationale");
  const explainList = document.getElementById("explain-list");
  const pulseBox = document.getElementById("pulse-alert-box");
  const pulseText = document.getElementById("pulse-alert-text");

  explainList.innerHTML = "";

  // Pulse Check
  if (pulse >= 100) {
    pulseBox.style.display = "flex";
    pulseText.textContent = `Tachycardia (${pulse} bpm): Check hydration & infection`;
  } else {
    pulseBox.style.display = "none";
  }

  let redTriggers = [];
  let yellowTriggers = [];

  // Vitals Check
  if (sbp >= 160 || dbp >= 110) {
    redTriggers.push(`Severe Hypertension (${sbp}/${dbp} mmHg) - Crisis Threshold`);
  } else if (sbp >= 140 || dbp >= 90) {
    yellowTriggers.push(`Hypertension (${sbp}/${dbp} mmHg) - Monitor Urine Albumin`);
  } else {
    explainList.innerHTML += `<li>Blood pressure ${sbp}/${dbp} mmHg is physiological.</li>`;
  }

  if (fhr < 110) {
    redTriggers.push(`Fetal Bradycardia (${fhr} bpm) - Urgent Hypoxia`);
  } else if (fhr > 160) {
    redTriggers.push(`Fetal Tachycardia (${fhr} bpm) - Distress`);
  } else {
    explainList.innerHTML += `<li>Fetal heart rate ${fhr} bpm is normal.</li>`;
  }

  if (hb < 7.0) {
    redTriggers.push(`Severe Anemia (${hb} g/dL) - Blood bank needed`);
  } else if (hb < 10.0) {
    yellowTriggers.push(`Moderate Anemia (${hb} g/dL) - AMTSL required`);
  }

  if (ga < 36) {
    redTriggers.push(`Preterm Labor (${ga} weeks) - NICU care required`);
  } else if (ga >= 41) {
    yellowTriggers.push(`Post-term Pregnancy (${ga} weeks)`);
  }

  if (rom) {
    yellowTriggers.push("Ruptured Membranes (PROM) - Ascending Infection Risk");
  }

  // Populate explanations
  redTriggers.forEach(t => {
    explainList.innerHTML += `<li style="color: #dc2626; font-weight: 600;">⚠️ [CRITICAL] ${t}</li>`;
  });
  yellowTriggers.forEach(t => {
    explainList.innerHTML += `<li style="color: #d97706; font-weight: 600;">⚡ [VIGILANCE] ${t}</li>`;
  });

  // Assign Decision
  if (redTriggers.length > 0) {
    card.className = "ai-card red";
    badge.textContent = "RED: IMMEDIATE REFERRAL";
    headline.textContent = "REFER TO SDH / DH IMMEDIATELY";
    rationale.textContent = "Critical emergency danger signs detected. Administer MgSO4 / O2 and transfer in ambulance.";
  } else if (yellowTriggers.length >= 2) {
    card.className = "ai-card yellow";
    badge.textContent = "YELLOW: PLANNED TRANSFER";
    headline.textContent = "REFER AFTER SENIOR REVIEW";
    rationale.textContent = "Multiple risk triggers noted. Evaluate with Senior Medical Officer for secondary referral.";
  } else if (yellowTriggers.length === 1) {
    card.className = "ai-card yellow";
    badge.textContent = "YELLOW: HIGH VIGILANCE";
    headline.textContent = "DO NOT REFER YET — MONITOR AT PHC";
    rationale.textContent = "Single risk trigger. Plot 30-min partograph. If labor does not progress, refer out.";
  } else {
    card.className = "ai-card green";
    badge.textContent = "GREEN: SAFE FOR PLHCU";
    headline.textContent = "DO NOT REFER — Routine Care";
    rationale.textContent = "Normal progress of labor. Standard supportive care at Primary Health Center.";
  }
}
