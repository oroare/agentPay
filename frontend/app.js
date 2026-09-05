const goalEl = document.getElementById("goal");
const budgetEl = document.getElementById("budget");
const upsellCapEl = document.getElementById("upsellCap");
const enableUpsellEl = document.getElementById("enableUpsell");
const simulateDeclineEl = document.getElementById("simulateDecline");
const runBtn = document.getElementById("runBtn");
const receiptEl = document.getElementById("receipt");
const timelineEl = document.getElementById("timeline");
const sessionMeta = document.getElementById("sessionMeta");

document.querySelectorAll(".presets button").forEach((button) => {
  button.addEventListener("click", () => {
    goalEl.value = button.dataset.goal;
    budgetEl.value = button.dataset.budget;
  });
});

runBtn.addEventListener("click", async () => {
  runBtn.disabled = true;
  receiptEl.textContent = "Agent is shopping…";
  timelineEl.innerHTML = "";
  sessionMeta.textContent = "";
  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        goal: goalEl.value,
        max_total_spend_inr: Number(budgetEl.value),
        max_upsell_amount_inr: Number(upsellCapEl.value),
        enable_upsell: enableUpsellEl.checked,
        simulate_decline: simulateDeclineEl.checked,
      }),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const result = await response.json();
    renderReceipt(result);
    await playTimeline(result.timeline);
    sessionMeta.textContent = result.session_id;
  } catch (error) {
    receiptEl.textContent = String(error);
  } finally {
    runBtn.disabled = false;
  }
});

function renderReceipt(result) {
  const items = (result.cart?.items || [])
    .map((item) => `${item.name} · ₹${item.price_inr}${item.is_upsell ? " (upsell)" : ""}`)
    .join("<br>");
  receiptEl.innerHTML = `
    <div class="receipt-card">
      <div class="stat"><span>Status</span><strong>${result.status}</strong></div>
      <div class="stat"><span>Parser</span><span>${result.parser}</span></div>
      <div class="stat"><span>Basket without upsell</span><span>₹${result.basket_without_upsell_inr}</span></div>
      <div class="stat"><span>Basket with upsell</span><span>₹${result.basket_with_upsell_inr}</span></div>
      <div class="stat"><span>Growth lift</span><span class="lift">+₹${result.lift_inr} (${result.lift_pct}%)</span></div>
      <div class="stat"><span>Payment</span><span>${result.payment?.status || "n/a"} ${result.payment?.order_id || ""}</span></div>
      <p>${result.receipt?.message || ""}</p>
      <p>${items || "No items"}</p>
      <p class="hint">${result.gate_one_liner}</p>
    </div>
  `;
}

async function playTimeline(events) {
  timelineEl.innerHTML = "";
  for (const [index, event] of events.entries()) {
    const li = document.createElement("li");
    li.style.animationDelay = `${index * 70}ms`;
    const klass = String(event.decision).toLowerCase();
    li.innerHTML = `
      <div class="actor">${event.actor}</div>
      <div>
        <div><strong>${event.action}</strong> · <span class="decision ${klass}">${event.decision}</span></div>
        <p class="reason">${event.reason}</p>
      </div>
    `;
    timelineEl.appendChild(li);
    await new Promise((resolve) => setTimeout(resolve, 90));
  }
}
