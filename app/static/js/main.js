/**
 * MatriSuraksha - Clinical Decision Support System & Interactive Workspace
 * Dakshin Dinajpur District Health Administration &bull; Government of West Bengal
 */

let currentAdmittedStudyId = "NEW-ADMISSION";
let isMaternalSaved = false;

document.addEventListener("DOMContentLoaded", function () {
    const intakeForm = document.getElementById("cdss-intake-form");
    if (intakeForm) {
        const allCard1Inputs = [
            "primary_unit_select", "primary_unit_custom", "block_name",
            "patient_name", "age", "matrima_id", "systolic_bp", "diastolic_bp", "pulse",
            "temp", "stage_of_labor", "labor_duration",
            "fetal_heart_rate", "presentation", "cervical_dilatation",
            "effacement", "station", "has_rom", "liquor_color",
            "gestational_age", "gravida", "parity_live", "parity_loss", "hemoglobin",
            "urine_albumin", "blood_sugar", "usg_placenta", "usg_afi", "prev_lucs", "has_prev_comp"
        ];

        allCard1Inputs.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener("input", debounce(checkSectionCompletion, 120));
                el.addEventListener("change", checkSectionCompletion);
            }
        });

        // Explicit click listeners for Step navigation buttons
        document.getElementById("btn-next-step-2")?.addEventListener("click", () => nextClinicalTab("tab-exam"));
        document.getElementById("btn-next-step-3")?.addEventListener("click", () => nextClinicalTab("tab-antenatal"));

        // Membrane status change listener
        document.getElementById("has_rom")?.addEventListener("change", handleMembraneStatusChange);
        handleMembraneStatusChange();

        // Initial validation check
        checkSectionCompletion();
    }

    // Initialize doctor re-evaluation time display
    calculateNextReevalTime();
});

function debounce(func, delay) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), delay);
    };
}

/**
 * Toast Notification Helper
 */
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast-pill ${type}`;

    let icon = "fa-circle-info";
    if (type === "success") icon = "fa-circle-check";
    if (type === "error" || type === "danger") icon = "fa-triangle-exclamation";
    if (type === "warning") icon = "fa-bell";

    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("show");
    }, 10);

    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

/**
 * Switch Clinical Form Tabs
 */
function switchClinicalTab(tabId) {
    document.querySelectorAll(".clinical-intake-form .tab-content").forEach(el => el.style.display = "none");
    document.querySelectorAll(".tracker-pill").forEach(el => el.classList.remove("active"));

    const target = document.getElementById(tabId);
    if (target) {
        target.style.display = "block";
    }

    if (tabId === 'tab-vitals') {
        document.getElementById('pill-sec-1')?.classList.add('active');
    } else if (tabId === 'tab-exam') {
        document.getElementById('pill-sec-2')?.classList.add('active');
    } else if (tabId === 'tab-antenatal') {
        document.getElementById('pill-sec-3')?.classList.add('active');
    }

    const form = document.getElementById("cdss-intake-form");
    if (form) {
        form.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
}

function nextClinicalTab(tabId) {
    switchClinicalTab(tabId);
}

function prevClinicalTab(tabId) {
    switchClinicalTab(tabId);
}

/**
 * Pre-fill Demo Clinical Cases for Rapid Demonstrations
 */
function loadClinicalPreset(type) {
    if (type === 'reset') {
        document.getElementById("cdss-intake-form")?.reset();
        isMaternalSaved = false;
        currentAdmittedStudyId = "NEW-ADMISSION";
        checkSectionCompletion();
        switchClinicalTab('tab-vitals');
        showToast("Clinical intake form cleared.", "info");
        return;
    }

    let p = {};
    if (type === 'normal') {
        p = {
            patient_name: "Kalyani Das",
            age: 23,
            matrima_id: "ANC-2026-9481",
            systolic_bp: 118,
            diastolic_bp: 76,
            pulse: 78,
            temp: 98.4,
            stage_of_labor: "Active Labour (First Stage)",
            labor_duration: 3.5,
            fetal_heart_rate: 142,
            presentation: "Vertex/Cephalic",
            cervical_dilatation: 4.5,
            effacement: 60,
            station: "0",
            has_rom: "0",
            liquor_color: "Clear",
            gestational_age: 39.2,
            gravida: 1,
            parity_live: 0,
            parity_loss: 0,
            hemoglobin: 11.6,
            urine_albumin: "Nil",
            blood_sugar: 92,
            usg_placenta: "Normal",
            usg_afi: "Adequate",
            prev_lucs: false,
            has_prev_comp: false
        };
        showToast("Loaded Normal Physiological Labor Case (Low Risk)", "success");
    } else if (type === 'moderate') {
        p = {
            patient_name: "Mousumi Khatun",
            age: 20,
            matrima_id: "ANC-2026-3312",
            systolic_bp: 136,
            diastolic_bp: 88,
            pulse: 104,
            temp: 99.1,
            stage_of_labor: "Active Labour (First Stage)",
            labor_duration: 7.0,
            fetal_heart_rate: 155,
            presentation: "Vertex/Cephalic",
            cervical_dilatation: 5.0,
            effacement: 70,
            station: "-1",
            has_rom: "1",
            liquor_color: "Thin Meconium (Grade 1)",
            gestational_age: 38.5,
            gravida: 2,
            parity_live: 1,
            parity_loss: 0,
            hemoglobin: 9.2,
            urine_albumin: "+",
            blood_sugar: 105,
            usg_placenta: "Normal",
            usg_afi: "Adequate",
            prev_lucs: false,
            has_prev_comp: false
        };
        showToast("Loaded Moderate Vigilance Case (Anemia & Tachycardia)", "warning");
    } else if (type === 'severe') {
        p = {
            patient_name: "Puja Sarkar",
            age: 28,
            matrima_id: "ANC-2026-7890",
            systolic_bp: 172,
            diastolic_bp: 114,
            pulse: 116,
            temp: 99.8,
            stage_of_labor: "Active Labour (First Stage)",
            labor_duration: 8.5,
            fetal_heart_rate: 102,
            presentation: "Vertex/Cephalic",
            cervical_dilatation: 4.0,
            effacement: 50,
            station: "-2",
            has_rom: "1",
            liquor_color: "Thick Meconium (Grade 2/3)",
            gestational_age: 37.0,
            gravida: 3,
            parity_live: 1,
            parity_loss: 1,
            hemoglobin: 8.4,
            urine_albumin: "+++",
            blood_sugar: 128,
            usg_placenta: "Low-lying",
            usg_afi: "Oligohydramnios",
            prev_lucs: true,
            has_prev_comp: true
        };
        showToast("Loaded Severe Crisis Case (Pre-Eclampsia / Fetal Distress)", "error");
    }

    // Apply values to inputs
    for (const [key, val] of Object.entries(p)) {
        const el = document.getElementById(key);
        if (el) {
            if (el.type === "checkbox") {
                el.checked = Boolean(val);
            } else {
                el.value = val;
            }
        }
    }

    // Trigger validation and update UI
    isMaternalSaved = false;
    handleMembraneStatusChange();
    checkSectionCompletion();
}

/**
 * Validates completion of all 3 clinical intake sections
 */
function checkSectionCompletion() {
    // SECTION 1: Demographics & Acute Maternal Vitals
    const nameVal = document.getElementById("patient_name")?.value.trim() || "";
    const ageVal = parseFloat(document.getElementById("age")?.value);
    const sbpVal = parseFloat(document.getElementById("systolic_bp")?.value);
    const dbpVal = parseFloat(document.getElementById("diastolic_bp")?.value);
    const pulseVal = parseFloat(document.getElementById("pulse")?.value);
    const tempVal = parseFloat(document.getElementById("temp")?.value);
    const stageVal = document.getElementById("stage_of_labor")?.value || "";

    const facSel = document.getElementById("primary_unit_select")?.value;
    const facCust = document.getElementById("primary_unit_custom")?.value.trim() || "";
    const facValid = (facSel && facSel !== "__ADD_NEW__") || facCust.length > 0 || (document.getElementById("primary_unit_select")?.options?.length > 1);

    const sec1Complete = Boolean(
        facValid &&
        nameVal.length > 0 &&
        !isNaN(ageVal) && ageVal >= 12 &&
        !isNaN(sbpVal) && sbpVal > 40 &&
        !isNaN(dbpVal) && dbpVal > 20 &&
        !isNaN(pulseVal) && pulseVal > 30 &&
        !isNaN(tempVal) && tempVal > 90 &&
        stageVal !== ""
    );

    // Pulse Badge Live Indicator (if present in DOM)
    const pBadge = document.getElementById("pulse-badge-ui");
    if (pBadge) {
        if (!isNaN(pulseVal) && pulseVal > 0) {
            if (pulseVal >= 100) {
                pBadge.className = "triage-badge red pulse-sub-badge";
                pBadge.textContent = "Tachycardia (" + Math.round(pulseVal) + " bpm)";
            } else if (pulseVal < 60) {
                pBadge.className = "triage-badge yellow pulse-sub-badge";
                pBadge.textContent = "Bradycardia (" + Math.round(pulseVal) + " bpm)";
            } else {
                pBadge.className = "triage-badge green pulse-sub-badge";
                pBadge.textContent = "Normal (" + Math.round(pulseVal) + " bpm)";
            }
        } else {
            pBadge.className = "triage-badge neutral pulse-sub-badge";
            pBadge.textContent = "Pending";
        }
    }

    // SECTION 2: Vaginal Examination & Fetus
    const fhrVal = parseFloat(document.getElementById("fetal_heart_rate")?.value);
    const presVal = document.getElementById("presentation")?.value || "";
    const cervixVal = document.getElementById("cervical_dilatation")?.value;
    const effaceVal = document.getElementById("effacement")?.value;
    const stationVal = document.getElementById("station")?.value || "";
    const romVal = document.getElementById("has_rom")?.value || "";
    const liquorVal = document.getElementById("liquor_color")?.value || "";

    // If membrane is intact (0), liquor color is NOT required.
    // If membrane is ruptured (1), liquor color IS required.
    const liquorValid = (romVal === "0") || (romVal === "1" && liquorVal !== "");

    const sec2Complete = Boolean(
        !isNaN(fhrVal) && fhrVal > 40 &&
        presVal !== "" &&
        cervixVal !== "" && !isNaN(parseFloat(cervixVal)) &&
        effaceVal !== "" && !isNaN(parseFloat(effaceVal)) &&
        stationVal !== "" &&
        romVal !== "" &&
        liquorValid
    );

    // SECTION 3: Antenatal Profile & Diagnostics
    const gaVal = parseFloat(document.getElementById("gestational_age")?.value);
    const gravVal = parseFloat(document.getElementById("gravida")?.value);
    const hbVal = parseFloat(document.getElementById("hemoglobin")?.value);
    const urineVal = document.getElementById("urine_albumin")?.value || "";
    const placVal = document.getElementById("usg_placenta")?.value || "";
    const afiVal = document.getElementById("usg_afi")?.value || "";

    const sec3Complete = Boolean(
        !isNaN(gaVal) && gaVal >= 20 &&
        !isNaN(gravVal) && gravVal >= 1 &&
        !isNaN(hbVal) && hbVal > 2 &&
        urineVal !== "" &&
        placVal !== "" &&
        afiVal !== ""
    );

    // Update Section Pills
    updatePillStatus("pill-sec-1", sec1Complete, "1", "Vitals & Labor");
    updatePillStatus("pill-sec-2", sec2Complete, "2", "Exam & Fetus");
    updatePillStatus("pill-sec-3", sec3Complete, "3", "Antenatal & Labs");

    // Activate Step 2 & Step 3 Navigation Buttons and Ready Pills
    const btnNext2 = document.getElementById("btn-next-step-2");
    const pill2 = document.getElementById("pill-sec-2");
    if (sec1Complete) {
        btnNext2?.classList.add("btn-step-ready");
        pill2?.classList.add("pill-ready");
    } else {
        btnNext2?.classList.remove("btn-step-ready");
        pill2?.classList.remove("pill-ready");
    }

    const btnNext3 = document.getElementById("btn-next-step-3");
    const pill3 = document.getElementById("pill-sec-3");
    if (sec2Complete) {
        btnNext3?.classList.add("btn-step-ready");
        pill3?.classList.add("pill-ready");
    } else {
        btnNext3?.classList.remove("btn-step-ready");
        pill3?.classList.remove("pill-ready");
    }

    // Update Progress Badge
    const completedCount = (sec1Complete ? 1 : 0) + (sec2Complete ? 1 : 0) + (sec3Complete ? 1 : 0);
    const countBadge = document.getElementById("tracker-count");
    if (countBadge) {
        if (completedCount === 3) {
            countBadge.className = "tracker-badge-complete";
            countBadge.innerHTML = '<i class="fa-solid fa-circle-check"></i> 3 / 3 Complete (Ready)';
        } else {
            countBadge.className = "tracker-badge-incomplete";
            countBadge.innerHTML = `<i class="fa-solid fa-circle-notch"></i> ${completedCount} / 3 Complete`;
        }
    }

    // Button Activation Logic
    const btnSave = document.getElementById("btn-save-maternal");
    const btnRunCDSS = document.getElementById("btn-run-ai-cdss");
    const statusHint = document.getElementById("intake-status-hint");

    if (!isMaternalSaved) {
        if (completedCount === 3) {
            if (btnSave) {
                btnSave.disabled = false;
                btnSave.classList.add("ready-to-save");
            }
            if (statusHint) {
                statusHint.className = "intake-status-hint ready";
                statusHint.innerHTML = '<i class="fa-solid fa-circle-check"></i> All 3 sections ready! Click <strong>1. Save Maternal Details</strong>.';
            }
        } else {
            if (btnSave) {
                btnSave.disabled = true;
                btnSave.classList.remove("ready-to-save");
            }
            if (btnRunCDSS) {
                btnRunCDSS.disabled = true;
                btnRunCDSS.classList.remove("unlocked-active");
            }
            if (statusHint) {
                statusHint.className = "intake-status-hint";
                statusHint.innerHTML = '<i class="fa-solid fa-circle-info"></i> Complete all 3 clinical sections above to activate <strong>1. Save Maternal Details</strong>, then run AI CDSS.';
            }
        }
    }

    return { sec1Complete, sec2Complete, sec3Complete, allComplete: completedCount === 3 };
}

function updatePillStatus(pillId, isComplete, stepNum, labelText) {
    const pill = document.getElementById(pillId);
    if (!pill) return;
    if (isComplete) {
        pill.classList.add("complete");
        const iconSpan = pill.querySelector(".pill-step-num");
        if (iconSpan) iconSpan.innerHTML = '<i class="fa-solid fa-check"></i>';
    } else {
        pill.classList.remove("complete");
        const iconSpan = pill.querySelector(".pill-step-num");
        if (iconSpan) iconSpan.textContent = stepNum;
    }
}

/**
 * Handle Step 1: Save Maternal Details to SQLite Registry
 */
async function handleSaveMaternalDetails() {
    const status = checkSectionCompletion();
    if (!status.allComplete) {
        if (!status.sec1Complete) {
            showToast("Section 1 (Vitals & Demographics) is incomplete.", "warning");
            switchClinicalTab("tab-vitals");
        } else if (!status.sec2Complete) {
            showToast("Section 2 (Vaginal Exam & Fetus) is incomplete.", "warning");
            switchClinicalTab("tab-exam");
        } else if (!status.sec3Complete) {
            showToast("Section 3 (Antenatal Profile & Labs) is incomplete.", "warning");
            switchClinicalTab("tab-antenatal");
        }
        return;
    }

    const payload = collectFormData();
    const btnSave = document.getElementById("btn-save-maternal");
    const btnRunCDSS = document.getElementById("btn-run-ai-cdss");
    const statusHint = document.getElementById("intake-status-hint");

    if (btnSave) {
        btnSave.disabled = true;
        btnSave.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Saving Patient Record...</span>';
    }

    try {
        const res = await fetch("/api/patient/admit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await res.json();

        if (result.success) {
            currentAdmittedStudyId = result.study_id;
            isMaternalSaved = true;

            if (btnSave) {
                btnSave.disabled = true;
                btnSave.classList.remove("ready-to-save");
                btnSave.classList.add("saved-success");
                btnSave.innerHTML = `<i class="fa-solid fa-circle-check"></i> <span>1. Saved (#${result.study_id})</span>`;
            }

            // Unlock Button 2: Run AI CDSS
            if (btnRunCDSS) {
                btnRunCDSS.disabled = false;
                btnRunCDSS.classList.add("unlocked-active");
            }

            if (statusHint) {
                statusHint.className = "intake-status-hint saved";
                statusHint.innerHTML = `<i class="fa-solid fa-circle-check"></i> Patient <strong>#${result.study_id}</strong> registered! Now click <strong>2. AI Based CDSS for Referral</strong>.`;
            }

            showToast(`Patient #${result.study_id} registered successfully! Now execute AI CDSS.`, "success");
        } else {
            showToast("Error saving record: " + (result.error || "Unknown"), "error");
            if (btnSave) {
                btnSave.disabled = false;
                btnSave.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> <span>1. Save Maternal Details</span>';
            }
        }
    } catch (err) {
        console.error(err);
        showToast("Network connection error: " + err.message, "error");
        if (btnSave) {
            btnSave.disabled = false;
            btnSave.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> <span>1. Save Maternal Details</span>';
        }
    }
}

/**
 * Handle Step 2: Run AI Based CDSS for Referral & SHAP Explainability
 */
async function handleRunAICDSS() {
    const payload = collectFormData();
    const btnRunCDSS = document.getElementById("btn-run-ai-cdss");

    if (btnRunCDSS) {
        btnRunCDSS.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Evaluating AI CDSS...</span>';
    }

    try {
        const response = await fetch("/api/cdss/evaluate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        updateCDSSAndSHAPUI(data);

        if (btnRunCDSS) {
            btnRunCDSS.innerHTML = '<i class="fa-solid fa-microchip"></i> <span>2. AI Based CDSS (Active)</span>';
        }

        showToast(`AI Triage Assigned: ${data.triage_level} (${data.risk_score}/100)`, data.triage_level === "RED" ? "danger" : (data.triage_level === "YELLOW" ? "warning" : "success"));

        // Highlight Card 2
        const card2 = document.querySelector(".card-2-triage");
        if (card2 && window.innerWidth <= 1080) {
            card2.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    } catch (err) {
        console.error("AI CDSS & SHAP Evaluation Error:", err);
        showToast("Error evaluating CDSS: " + err.message, "error");
        if (btnRunCDSS) {
            btnRunCDSS.innerHTML = '<i class="fa-solid fa-microchip"></i> <span>2. AI Based CDSS for Referral</span>';
        }
    }
}

function collectFormData() {
    let facName = "";
    const facSelect = document.getElementById("primary_unit_select");
    const facCustom = document.getElementById("primary_unit_custom");
    if (facSelect && facSelect.value && facSelect.value !== "__ADD_NEW__") {
        facName = facSelect.value.trim();
    } else if (facCustom && facCustom.value.trim()) {
        facName = facCustom.value.trim();
    } else {
        facName = "Primary Health Center";
    }

    const blockName = document.getElementById("block_name")?.value.trim() || "";

    return {
        facility_name: facName,
        block_name: blockName,
        patient_name: document.getElementById("patient_name")?.value.trim() || "Mother",
        age: parseFloat(document.getElementById("age")?.value) || 24,
        matrima_id: document.getElementById("matrima_id")?.value.trim() || "",
        systolic_bp: parseFloat(document.getElementById("systolic_bp")?.value) || 120,
        diastolic_bp: parseFloat(document.getElementById("diastolic_bp")?.value) || 80,
        pulse: parseFloat(document.getElementById("pulse")?.value) || 78,
        temp: parseFloat(document.getElementById("temp")?.value) || 98.4,
        stage_of_labor: document.getElementById("stage_of_labor")?.value || "Active Labour (First Stage)",
        labor_duration: parseFloat(document.getElementById("labor_duration")?.value) || 4,
        hemoglobin: parseFloat(document.getElementById("hemoglobin")?.value) || 11.0,
        fetal_heart_rate: parseFloat(document.getElementById("fetal_heart_rate")?.value) || 140,
        gestational_age: parseFloat(document.getElementById("gestational_age")?.value) || 39.0,
        cervical_dilatation: parseFloat(document.getElementById("cervical_dilatation")?.value) || 4,
        effacement: parseFloat(document.getElementById("effacement")?.value) || 60,
        station: document.getElementById("station")?.value || "0",
        presentation: document.getElementById("presentation")?.value || "Vertex/Cephalic",
        has_rom: document.getElementById("has_rom")?.value || "0",
        liquor_color: (document.getElementById("has_rom")?.value === "1") ? (document.getElementById("liquor_color")?.value || "Clear") : "Clear",
        gravida: parseInt(document.getElementById("gravida")?.value) || 1,
        parity_live: parseInt(document.getElementById("parity_live")?.value) || 0,
        parity_loss: parseInt(document.getElementById("parity_loss")?.value) || 0,
        urine_albumin: document.getElementById("urine_albumin")?.value || "Nil",
        blood_sugar: parseFloat(document.getElementById("blood_sugar")?.value) || 92,
        usg_placenta: document.getElementById("usg_placenta")?.value || "Normal",
        usg_afi: document.getElementById("usg_afi")?.value || "Adequate",
        prev_lucs: document.getElementById("prev_lucs")?.checked ? 1 : 0,
        has_prev_comp: document.getElementById("has_prev_comp")?.checked ? 1 : 0
    };
}

function updateCDSSAndSHAPUI(data) {
    const alertBox = document.getElementById("cdss-alert-box");
    const badge = document.getElementById("triage-badge");
    const headline = document.getElementById("ai-decision-headline");
    const scoreVal = document.getElementById("cdss-score-val");
    const gaugeFill = document.getElementById("risk-gauge-fill");
    const destText = document.getElementById("cdss-dest-text");
    const triggersList = document.getElementById("cdss-triggers-list");
    const protocolsList = document.getElementById("cdss-protocols-list");
    const pulseContainer = document.getElementById("pulse-highlight-container");
    const pulseText = document.getElementById("pulse-highlight-text");
    const referBtn = document.getElementById("quick-refer-btn");

    if (!alertBox) return;

    const tLevel = (data.triage_level || "GREEN").toLowerCase();

    // Triage Styling
    alertBox.className = "cdss-grid-card-body cdss-alert-box " + tLevel;
    if (badge) {
        badge.className = "triage-badge " + tLevel;
        badge.textContent = data.triage_level + " TRIAGE";
    }

    // Risk Score & Visual Meter
    if (scoreVal) scoreVal.textContent = Math.round(data.risk_score);
    if (gaugeFill) {
        const score = Math.max(0, Math.min(100, data.risk_score || 0));
        gaugeFill.style.width = score + "%";
        if (score >= 70) {
            gaugeFill.style.background = "linear-gradient(90deg, #f59e0b, #ef4444)";
        } else if (score >= 30) {
            gaugeFill.style.background = "linear-gradient(90deg, #10b981, #f59e0b)";
        } else {
            gaugeFill.style.background = "#10b981";
        }
    }

    const riskTag = document.getElementById("cdss-risk-tag");
    if (riskTag) {
        riskTag.className = "score-status-pill " + tLevel;
        if (data.triage_level === "RED") {
            riskTag.textContent = "Critical Referral Crisis";
        } else if (data.triage_level === "YELLOW") {
            riskTag.textContent = "Moderate Vigilance Required";
        } else {
            riskTag.textContent = "Physiological Labor";
        }
    }

    if (destText) {
        destText.innerHTML = `<strong>${data.recommended_destination}</strong> &bull; ${data.urgency}`;
    }

    // Headline
    if (headline) {
        headline.className = "ai-hero-decision " + tLevel;
        let iconHtml = '<i class="fa-solid fa-shield-halved"></i>';
        let leadText = "AI CLINICAL DECISION";
        let mainText = data.ai_decision;

        if (data.triage_level === "RED") {
            iconHtml = '<i class="fa-solid fa-triangle-exclamation"></i>';
            leadText = "CRITICAL EMERGENCY ACTION";
            mainText = "REFER IMMEDIATELY (EMERGENCY TRANSFER)";
            if (referBtn) referBtn.style.display = "inline-flex";
        } else if (data.triage_level === "YELLOW") {
            iconHtml = '<i class="fa-solid fa-eye"></i>';
            leadText = "SPECIALIST VIGILANCE REQUIRED";
            if (referBtn) referBtn.style.display = data.referral_recommended ? "inline-flex" : "none";
        } else {
            iconHtml = '<i class="fa-solid fa-circle-check"></i>';
            leadText = "PHYSIOLOGICAL STATUS";
            mainText = "DO NOT REFER — SAFE FOR NORMAL PLHCU DELIVERY";
            if (referBtn) referBtn.style.display = "none";
        }

        headline.innerHTML = `
            ${iconHtml}
            <div class="ai-decision-text-wrap">
                <span class="ai-decision-lead">${leadText}</span>
                <strong class="ai-decision-title">${mainText}</strong>
            </div>
        `;
    }

    // Pulse Alert
    if (pulseContainer && pulseText) {
        if (data.pulse_highlight && data.pulse_highlight.status !== "NORMAL") {
            pulseContainer.style.display = "flex";
            pulseText.textContent = data.pulse_highlight.alert_message;
        } else {
            pulseContainer.style.display = "none";
        }
    }

    // Danger Signs / Clinical Findings
    if (triggersList) {
        triggersList.innerHTML = "";
        if (data.triggers && data.triggers.length > 0) {
            data.triggers.forEach(t => {
                const li = document.createElement("li");
                const sev = (t.severity || "warning").toLowerCase();
                const sevClass = (sev.includes("critical") ? "critical" : (sev.includes("red") ? "critical" : (sev.includes("yellow") ? "warning" : "info")));
                li.className = "trigger-item " + sevClass;
                li.innerHTML = `
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <div>
                        <strong>[${t.severity}] ${t.title}:</strong>
                        <span>${t.action || t.text}</span>
                    </div>
                `;
                triggersList.appendChild(li);
            });
        } else {
            const li = document.createElement("li");
            li.className = "trigger-item normal";
            li.innerHTML = '<i class="fa-solid fa-circle-check"></i> <span>All vital parameters, maternal pulse, and fetal heart rate are physiological. Safe for PLHCU delivery.</span>';
            triggersList.appendChild(li);
        }
    }

    // Stabilization Protocols
    if (protocolsList && data.stabilization_protocols) {
        protocolsList.innerHTML = "";
        data.stabilization_protocols.forEach(p => {
            const li = document.createElement("li");
            li.className = "protocol-item";
            li.innerHTML = `<i class="fa-solid fa-check"></i> <span>${p}</span>`;
            protocolsList.appendChild(li);
        });
    }

    // Render SHAP Waterfall
    renderSHAPWaterfall(data.shap);
}

function renderSHAPWaterfall(shapData) {
    const container = document.getElementById("shap-waterfall-container");
    const probBadge = document.getElementById("shap-prediction-badge");
    const guideBox = document.getElementById("shap-guidelines-box");

    if (!container || !shapData) return;

    if (probBadge) {
        const prob = Math.round((shapData.prediction_prob || 0) * 100);
        const base = Math.round((shapData.base_value || 0.49) * 100);
        probBadge.textContent = `Model Risk: ${prob}% (Base: ${base}%)`;
        probBadge.className = "shap-prob-badge " + (prob >= 70 ? "red" : (prob >= 30 ? "yellow" : "green"));
    }

    container.innerHTML = "";
    if (guideBox) guideBox.innerHTML = "";

    const contributions = shapData.shap_contributions || [];
    if (contributions.length === 0) {
        container.innerHTML = '<div class="shap-empty-state"><p>Evaluating SHAP feature attributions...</p></div>';
        return;
    }

    const maxVal = Math.max(...contributions.map(c => Math.abs(c.shap_value)), 0.05);

    contributions.slice(0, 7).forEach(c => {
        const isRed = c.impact === "INCREASES_RISK";
        const barWidth = Math.min(100, Math.max(10, (Math.abs(c.shap_value) / maxVal) * 100));

        const row = document.createElement("div");
        row.className = "shap-bar-row";
        row.innerHTML = `
            <span class="shap-feat-name" title="${c.feature}: ${c.display_value}">
                <strong>${c.feature}</strong> <span class="feat-val">(${c.display_value})</span>
            </span>
            <div class="shap-bar-track">
                <div class="shap-bar-fill ${isRed ? 'red' : 'blue'}" style="width: ${barWidth}%;"></div>
            </div>
            <span class="shap-val-tag ${isRed ? 'text-red' : 'text-blue'}">
                ${c.shap_value > 0 ? '+' : ''}${c.shap_value.toFixed(3)}
            </span>
        `;
        container.appendChild(row);
    });

    if (guideBox && shapData.top_drivers && shapData.top_drivers.length > 0) {
        const top = shapData.top_drivers[0];
        guideBox.innerHTML = `
            <i class="fa-solid fa-circle-info"></i>
            <div>
                <strong>Primary Clinical Risk Driver:</strong> ${top.feature} (${top.display_value}) &bull;
                <em>${top.guideline}</em>
            </div>
        `;
    }
}

function triggerQuickReferralSlip() {
    const studyId = currentAdmittedStudyId || "NEW-ADMISSION";
    const patientName = document.getElementById("patient_name")?.value || "Mother";
    const triggers = document.getElementById("cdss-triggers-list")?.innerText || "High-risk intrapartum danger signs detected";
    openReferralModal(studyId, patientName, "RED", triggers);
}

// -------------------------------------------------------------
// Clinical Dynamic Field Visibility Handlers
// -------------------------------------------------------------
function handleMembraneStatusChange() {
    const romSelect = document.getElementById("has_rom");
    const liquorRow = document.getElementById("liquor_color_row");
    const liquorSelect = document.getElementById("liquor_color");
    if (!romSelect) return;

    if (romSelect.value === "1") {
        // Ruptured Membranes: Liquor color is required
        if (liquorRow) liquorRow.style.display = "grid";
        if (liquorSelect) {
            liquorSelect.setAttribute("required", "required");
        }
    } else {
        // Intact Membranes (0) or Unselected: Liquor color is NOT required
        if (liquorRow) liquorRow.style.display = "none";
        if (liquorSelect) {
            liquorSelect.removeAttribute("required");
            if (romSelect.value === "0") {
                liquorSelect.value = "Clear";
            }
        }
    }
    checkSectionCompletion();
}

// -------------------------------------------------------------
// Referral Dispatch & Modal Functions
// -------------------------------------------------------------
function handlePrimaryUnitChange() {
    const sel = document.getElementById("primary_unit_select");
    const group = document.getElementById("primary_unit_custom_group");
    const input = document.getElementById("primary_unit_custom");
    if (!sel || !group) return;
    if (sel.value === "__ADD_NEW__") {
        group.style.display = "block";
        if (input) input.focus();
    } else {
        group.style.display = "none";
    }
    checkSectionCompletion();
}

function handleOptionBDestChange() {
    const sel = document.getElementById("option-b-dest-select");
    const cust = document.getElementById("option-b-dest-custom");
    if (!sel || !cust) return;
    if (sel.value === "__ADD_NEW__") {
        cust.style.display = "block";
        cust.focus();
    } else {
        cust.style.display = "none";
    }
}

function handleReferralModalDestChange() {
    const sel = document.getElementById("referral-dest-select");
    const cust = document.getElementById("referral_dest_custom");
    if (!sel || !cust) return;
    if (sel.value === "__ADD_NEW__") {
        cust.style.display = "block";
        cust.focus();
    } else {
        cust.style.display = "none";
    }
}

function openReferralModal(studyId, patientName, triageLevel, triggers) {
    const modal = document.getElementById("referral-modal");
    if (!modal) return;

    document.getElementById("modal-study-id").textContent = studyId || "0000";
    document.getElementById("modal-patient-name").textContent = patientName || "Mother";
    
    const badge = document.getElementById("modal-triage-badge");
    if (badge) {
        badge.className = "triage-badge " + (triageLevel || "RED").toLowerCase();
        badge.textContent = triageLevel || "RED";
    }

    const idInput = document.getElementById("referral-study-id-input");
    if (idInput) idInput.value = studyId || "";

    const reasonInput = document.getElementById("referral-reason-input");
    if (reasonInput) reasonInput.value = triggers || "High-risk intrapartum progression transferred for specialist intervention.";

    // Sync destination from Option B if selected/entered
    const optBDestSel = document.getElementById("option-b-dest-select");
    const optBDestCust = document.getElementById("option-b-dest-custom");
    const refDestSel = document.getElementById("referral-dest-select");
    const refDestCust = document.getElementById("referral_dest_custom");
    if (optBDestSel && refDestSel) {
        if (optBDestSel.value && optBDestSel.value !== "__ADD_NEW__") {
            refDestSel.value = optBDestSel.value;
            if (refDestCust) refDestCust.style.display = "none";
        } else if (optBDestCust && optBDestCust.value.trim()) {
            refDestSel.value = "__ADD_NEW__";
            if (refDestCust) {
                refDestCust.value = optBDestCust.value.trim();
                refDestCust.style.display = "block";
            }
        }
    }

    modal.style.display = "flex";
}

function closeReferralModal() {
    const modal = document.getElementById("referral-modal");
    if (modal) modal.style.display = "none";
}

async function submitReferralDispatch(e) {
    e.preventDefault();
    const studyId = document.getElementById("referral-study-id-input")?.value;
    const destSelect = document.getElementById("referral-dest-select")?.value;
    const destCustom = document.getElementById("referral_dest_custom")?.value.trim() || "";
    
    let dest = "";
    if (destSelect && destSelect !== "__ADD_NEW__") {
        dest = destSelect;
    } else if (destCustom) {
        dest = destCustom;
    } else {
        dest = "Designated Referral Hospital";
    }

    const reason = document.getElementById("referral-reason-input")?.value || "Intrapartum complication";

    try {
        const res = await fetch("/api/patient/refer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ study_id: studyId, referral_facility: dest, reason: reason })
        });
        const data = await res.json();
        if (data.success) {
            closeReferralModal();
            showToast(`Referral Slip confirmed for #${studyId}! Dispatched to ${dest}.`, "success");
            setTimeout(() => window.location.reload(), 1200);
        } else {
            showToast("Referral dispatch error: " + (data.error || "Failed"), "error");
        }
    } catch (err) {
        showToast("Network error dispatching referral: " + err.message, "error");
    }
}

// -------------------------------------------------------------
// Module 2: Closed-Loop Referral Feedback Modal Helpers
// -------------------------------------------------------------
function openFeedbackModal(studyId, patientName, referringPhc, reason, refFacility) {
    const modal = document.getElementById("feedback-modal");
    if (!modal) return;

    const idSpan = document.getElementById("fb-study-id");
    const nameSpan = document.getElementById("fb-patient-name");
    const phcSpan = document.getElementById("fb-referring-phc");
    const reasonSpan = document.getElementById("fb-reason");
    const idInput = document.getElementById("fb-study-id-input");
    const facInput = document.getElementById("fb-referral-facility-input");

    if (idSpan) idSpan.textContent = "#" + studyId;
    if (nameSpan) nameSpan.textContent = patientName || "Mother";
    if (phcSpan) phcSpan.textContent = referringPhc || "Feeder Unit";
    if (reasonSpan) reasonSpan.textContent = reason || "Emergency transfer";
    if (idInput) idInput.value = studyId;
    if (facInput && refFacility) facInput.value = refFacility;

    modal.style.display = "flex";
}

function closeFeedbackModal() {
    const modal = document.getElementById("feedback-modal");
    if (modal) modal.style.display = "none";
}

async function submitReceivingFeedback(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const payload = {};
    formData.forEach((val, key) => { payload[key] = val; });

    try {
        const res = await fetch("/api/referral/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            closeFeedbackModal();
            showToast(`Closed-Loop Feedback transmitted for Patient #${payload.study_id}!`, "success");
            setTimeout(() => window.location.reload(), 1200);
        } else {
            showToast("Feedback submission failed: " + (data.error || "Unknown"), "error");
        }
    } catch (err) {
        showToast("Server communication error: " + err.message, "error");
    }
}

// -------------------------------------------------------------
// Attending Doctor Clinical Evaluation & Disposition Helpers
// -------------------------------------------------------------
function calculateNextReevalTime() {
    const sel = document.getElementById("reeval-hours-select");
    const custom = document.getElementById("reeval-custom-hours");
    const display = document.getElementById("next-reeval-time-display");
    if (!sel || !display) return;

    let hours = parseFloat(sel.value);
    if (sel.value === "custom") {
        if (custom) custom.style.display = "inline-block";
        hours = parseFloat(custom ? custom.value : 1) || 1;
    } else {
        if (custom) custom.style.display = "none";
    }

    const now = new Date();
    const future = new Date(now.getTime() + hours * 60 * 60 * 1000);
    const timeStr = future.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    display.textContent = timeStr + " (" + hours + "h)";
}

function toggleDoctorOverride(isOverride) {
    const box = document.getElementById("doctor-contradiction-inputs");
    if (box) {
        box.style.display = isOverride ? "block" : "none";
    }
}

function selectDisposition(val) {
    const radio = document.querySelector(`input[name="doctor_final_disposition"][value="${val}"]`);
    if (radio) {
        radio.checked = true;
    }
    const destWrap = document.getElementById("option-b-dest-wrap");
    if (destWrap) {
        destWrap.style.display = (val === 'REFER') ? "block" : "none";
    }
}

function handleDispRadio() {
    const radio = document.querySelector('input[name="doctor_final_disposition"]:checked');
    const destWrap = document.getElementById("option-b-dest-wrap");
    if (destWrap && radio) {
        destWrap.style.display = (radio.value === 'REFER') ? "block" : "none";
    }
}

async function saveDoctorClinicalOrder() {
    const agreeRadio = document.querySelector('input[name="doctor_decision_eval"]:checked');
    const dispRadio = document.querySelector('input[name="doctor_final_disposition"]:checked');

    const decision = agreeRadio ? agreeRadio.value : "AGREE";
    const action = dispRadio ? dispRadio.value : "REEVALUATE";

    const reasonCat = document.getElementById("doc_override_category")?.value || "";
    const reasonNotes = document.getElementById("doc_override_notes")?.value || "";
    const overrideReason = decision === "OVERRIDE" ? (reasonCat + ": " + reasonNotes) : "";

    const hoursSel = document.getElementById("reeval-hours-select");
    const customHours = document.getElementById("reeval-custom-hours");
    let reevalHours = hoursSel ? (hoursSel.value === "custom" ? (parseFloat(customHours?.value) || 1) : parseFloat(hoursSel.value)) : 1.0;
    const nextReevalTime = document.getElementById("next-reeval-time-display")?.textContent || "";

    const payload = {
        study_id: currentAdmittedStudyId,
        doctor_decision: decision,
        doctor_action: action,
        override_reason: overrideReason,
        reeval_hours: reevalHours,
        next_reeval_time: nextReevalTime
    };

    if (action === "REFER") {
        const bDestSel = document.getElementById("option-b-dest-select")?.value;
        const bDestCust = document.getElementById("option-b-dest-custom")?.value.trim() || "";
        const bDest = (bDestSel && bDestSel !== "__ADD_NEW__") ? bDestSel : (bDestCust || "Designated Referral Hospital");
        // Dispatch referral in background
        fetch("/api/patient/refer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ study_id: currentAdmittedStudyId, referral_facility: bDest, reason: "Doctor Ordered Referral" })
        }).catch(err => console.error("Error auto-referring:", err));
    }

    try {
        const resp = await fetch("/api/doctor/evaluation", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const res = await resp.json();
        if (res.success) {
            showToast(`Final Decision taken by attending doctor recorded for #${currentAdmittedStudyId}!`, "success");
        } else {
            showToast("Error saving doctor order: " + (res.error || "Unknown"), "error");
        }
    } catch (e) {
        console.error(e);
        showToast("Failed to submit doctor order.", "error");
    }
}

function toggleMISRegistry() {
    const body = document.getElementById("mis-registry-body");
    const icon = document.getElementById("mis-toggle-icon");
    if (!body) return;
    if (body.style.display === "none") {
        body.style.display = "block";
        if (icon) icon.innerHTML = '<i class="fa-solid fa-chevron-down"></i>';
    } else {
        body.style.display = "none";
        if (icon) icon.innerHTML = '<i class="fa-solid fa-chevron-up"></i>';
    }
}
