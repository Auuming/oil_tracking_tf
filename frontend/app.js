const DEMO_HISTORY = [
  {
    retailer: "PTT",
    oilType: "Gasohol 95",
    points: [
      { time: "2026-04-01 09:00", price: 36.8 },
      { time: "2026-04-02 09:00", price: 36.9 },
      { time: "2026-04-03 09:00", price: 37.0 },
      { time: "2026-04-04 09:00", price: 37.05 },
      { time: "2026-04-05 09:00", price: 37.15 },
      { time: "2026-04-06 09:00", price: 37.24 }
    ]
  },
  {
    retailer: "PTT",
    oilType: "Diesel",
    points: [
      { time: "2026-04-01 09:00", price: 31.4 },
      { time: "2026-04-02 09:00", price: 31.5 },
      { time: "2026-04-03 09:00", price: 31.62 },
      { time: "2026-04-04 09:00", price: 31.7 },
      { time: "2026-04-05 09:00", price: 31.82 },
      { time: "2026-04-06 09:00", price: 31.94 }
    ]
  },
  {
    retailer: "Bangchak",
    oilType: "Gasohol 95",
    points: [
      { time: "2026-04-01 09:00", price: 36.7 },
      { time: "2026-04-02 09:00", price: 36.78 },
      { time: "2026-04-03 09:00", price: 36.9 },
      { time: "2026-04-04 09:00", price: 36.95 },
      { time: "2026-04-05 09:00", price: 37.05 },
      { time: "2026-04-06 09:00", price: 37.14 }
    ]
  },
  {
    retailer: "Bangchak",
    oilType: "Diesel",
    points: [
      { time: "2026-04-01 09:00", price: 31.2 },
      { time: "2026-04-02 09:00", price: 31.28 },
      { time: "2026-04-03 09:00", price: 31.38 },
      { time: "2026-04-04 09:00", price: 31.44 },
      { time: "2026-04-05 09:00", price: 31.56 },
      { time: "2026-04-06 09:00", price: 31.64 }
    ]
  },
  {
    retailer: "Shell",
    oilType: "Gasohol 95",
    points: [
      { time: "2026-04-01 09:00", price: 37.6 },
      { time: "2026-04-02 09:00", price: 37.72 },
      { time: "2026-04-03 09:00", price: 37.82 },
      { time: "2026-04-04 09:00", price: 37.9 },
      { time: "2026-04-05 09:00", price: 37.96 },
      { time: "2026-04-06 09:00", price: 38.04 }
    ]
  },
  {
    retailer: "Shell",
    oilType: "Diesel",
    points: [
      { time: "2026-04-01 09:00", price: 31.8 },
      { time: "2026-04-02 09:00", price: 31.92 },
      { time: "2026-04-03 09:00", price: 32.0 },
      { time: "2026-04-04 09:00", price: 32.08 },
      { time: "2026-04-05 09:00", price: 32.16 },
      { time: "2026-04-06 09:00", price: 32.24 }
    ]
  }
];

const retailerSelect = document.getElementById("retailerSelect");
const oilTypeSelect = document.getElementById("oilTypeSelect");
const alertRetailerSelect = document.getElementById("alertRetailerSelect");
const alertOilTypeSelect = document.getElementById("alertOilTypeSelect");
const addSeriesBtn = document.getElementById("addSeriesBtn");
const clearSeriesBtn = document.getElementById("clearSeriesBtn");
const refreshBtn = document.getElementById("refreshBtn");
const selectedSeriesContainer = document.getElementById("selectedSeriesContainer");
const chartStatus = document.getElementById("chartStatus");
const latestCards = document.getElementById("latestCards");
const latestPriceTableBody = document.getElementById("latestPriceTableBody");
const alertForm = document.getElementById("alertForm");
const alertResult = document.getElementById("alertResult");
const backendStatus = document.getElementById("backendStatus");

let allHistory = [];
let selectedSeriesKeys = [];
let chart = null;

function uniqueValues(items, key) {
  return [...new Set(items.map(item => item[key]))].sort();
}

function buildSeriesKey(retailer, oilType) {
  return `${retailer}__${oilType}`;
}

function parseSeriesKey(key) {
  const [retailer, oilType] = key.split("__");
  return { retailer, oilType };
}

function getSeriesLabel(series) {
  return `${series.retailer} - ${series.oilType}`;
}

function getSeriesByKey(key) {
  const { retailer, oilType } = parseSeriesKey(key);
  return allHistory.find(item => item.retailer === retailer && item.oilType === oilType);
}

function setSelectOptions(selectElement, values) {
  selectElement.innerHTML = "";
  values.forEach(value => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    selectElement.appendChild(option);
  });
}

function populateControls() {
  const retailers = uniqueValues(allHistory, "retailer");
  const oilTypes = uniqueValues(allHistory, "oilType");

  setSelectOptions(retailerSelect, retailers);
  setSelectOptions(oilTypeSelect, oilTypes);
  setSelectOptions(alertRetailerSelect, retailers);
  setSelectOptions(alertOilTypeSelect, oilTypes);
}

function getLatestItems() {
  return allHistory.map(series => {
    const latestPoint = series.points[series.points.length - 1];
    return {
      retailer: series.retailer,
      oilType: series.oilType,
      price: latestPoint.price,
      updatedAt: latestPoint.time
    };
  });
}

function renderLatestSummary() {
  const latestItems = getLatestItems();

  if (!latestItems.length) {
    latestCards.innerHTML = `<p class="empty-state">No latest data available.</p>`;
    return;
  }

  const prices = latestItems.map(item => item.price);
  const minPrice = Math.min(...prices).toFixed(2);
  const maxPrice = Math.max(...prices).toFixed(2);
  const avgPrice = (prices.reduce((sum, p) => sum + p, 0) / prices.length).toFixed(2);
  const totalSeries = latestItems.length;

  latestCards.innerHTML = `
    <div class="stat-card">
      <div class="label">Tracked Series</div>
      <div class="value">${totalSeries}</div>
    </div>
    <div class="stat-card">
      <div class="label">Min Price</div>
      <div class="value">${minPrice}</div>
    </div>
    <div class="stat-card">
      <div class="label">Max Price</div>
      <div class="value">${maxPrice}</div>
    </div>
    <div class="stat-card">
      <div class="label">Average Price</div>
      <div class="value">${avgPrice}</div>
    </div>
  `;
}

function renderLatestTable() {
  const latestItems = getLatestItems();
  latestPriceTableBody.innerHTML = "";

  latestItems.forEach(item => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${item.retailer}</td>
      <td>${item.oilType}</td>
      <td>${item.price.toFixed(2)}</td>
      <td>${item.updatedAt}</td>
    `;
    latestPriceTableBody.appendChild(row);
  });
}

function renderSelectedChips() {
  selectedSeriesContainer.innerHTML = "";

  if (!selectedSeriesKeys.length) {
    selectedSeriesContainer.innerHTML = `<span class="empty-state">No series selected yet.</span>`;
    return;
  }

  selectedSeriesKeys.forEach(key => {
    const series = getSeriesByKey(key);
    if (!series) return;

    const chip = document.createElement("div");
    chip.className = "chip";
    chip.innerHTML = `
      <span>${getSeriesLabel(series)}</span>
      <button type="button" aria-label="Remove series">&times;</button>
    `;

    chip.querySelector("button").addEventListener("click", () => {
      selectedSeriesKeys = selectedSeriesKeys.filter(item => item !== key);
      renderSelectedChips();
      renderChart();
    });

    selectedSeriesContainer.appendChild(chip);
  });
}

function renderChart() {
  const canvas = document.getElementById("priceChart");

  if (chart) {
    chart.destroy();
  }

  const selectedSeries = selectedSeriesKeys
    .map(getSeriesByKey)
    .filter(Boolean);

  if (!selectedSeries.length) {
    chart = new Chart(canvas, {
      type: "line",
      data: { labels: [], datasets: [] },
      options: {
        responsive: true,
        maintainAspectRatio: false
      }
    });
    chartStatus.textContent = "No series selected.";
    return;
  }

  const labels = selectedSeries[0].points.map(point => point.time);

  const datasets = selectedSeries.map(series => ({
    label: getSeriesLabel(series),
    data: series.points.map(point => point.price),
    tension: 0.25,
    fill: false
  }));

  chart = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        legend: {
          position: "top"
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: "Time"
          }
        },
        y: {
          title: {
            display: true,
            text: "Price (THB/L)"
          }
        }
      }
    }
  });

  chartStatus.textContent = `Showing ${selectedSeries.length} selected series.`;
}

function addSelectedSeries() {
  const key = buildSeriesKey(retailerSelect.value, oilTypeSelect.value);

  if (!getSeriesByKey(key)) {
    chartStatus.textContent = "Selected combination is not available.";
    return;
  }

  if (selectedSeriesKeys.includes(key)) {
    chartStatus.textContent = "That series is already on the graph.";
    return;
  }

  selectedSeriesKeys.push(key);
  renderSelectedChips();
  renderChart();
}

function clearAllSeries() {
  selectedSeriesKeys = [];
  renderSelectedChips();
  renderChart();
}

async function fetchHistory() {
  if (!CONFIG.API_BASE_URL) {
    backendStatus.textContent = "Demo Mode";
    return { items: DEMO_HISTORY, mode: "demo" };
  }

  const response = await fetch(`${CONFIG.API_BASE_URL}/prices/history`);
  if (!response.ok) {
    throw new Error(`History request failed with status ${response.status}`);
  }

  const data = await response.json();
  backendStatus.textContent = "Connected";
  return { items: data.items || [], mode: "api" };
}

async function loadData() {
  chartStatus.textContent = "Loading data...";

  try {
    const result = await fetchHistory();
    allHistory = result.items;

    populateControls();
    renderLatestSummary();
    renderLatestTable();

    if (!selectedSeriesKeys.length && allHistory.length) {
      selectedSeriesKeys = [buildSeriesKey(allHistory[0].retailer, allHistory[0].oilType)];
    }

    renderSelectedChips();
    renderChart();

    if (result.mode === "demo") {
      chartStatus.textContent = "Loaded demo data. Backend not connected yet.";
    }
  } catch (error) {
    console.error(error);
    chartStatus.textContent = "Failed to load data.";
    backendStatus.textContent = "Error";
  }
}

async function submitAlert(event) {
  event.preventDefault();

  const payload = {
    email: document.getElementById("emailInput").value.trim(),
    retailer: alertRetailerSelect.value,
    oilType: alertOilTypeSelect.value,
    condition: document.getElementById("conditionSelect").value,
    targetPrice: Number(document.getElementById("targetPriceInput").value)
  };

  if (!payload.email || !payload.retailer || !payload.oilType || !payload.condition || Number.isNaN(payload.targetPrice)) {
    alertResult.className = "alert-box";
    alertResult.textContent = "Please fill in all alert fields correctly.";
    return;
  }

  if (!CONFIG.API_BASE_URL) {
    alertResult.className = "alert-box success";
    alertResult.textContent =
      `Demo mode: alert prepared for ${payload.email} | ${payload.retailer} | ${payload.oilType} ${payload.condition} ${payload.targetPrice.toFixed(2)} THB/L`;
    return;
  }

  try {
    const response = await fetch(`${CONFIG.API_BASE_URL}/alerts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.message || "Failed to create alert");
    }

    alertResult.className = "alert-box success";
    alertResult.textContent = result.message || "Alert created successfully.";
    alertForm.reset();
    populateControls();
  } catch (error) {
    console.error(error);
    alertResult.className = "alert-box";
    alertResult.textContent = error.message;
  }
}

addSeriesBtn.addEventListener("click", addSelectedSeries);
clearSeriesBtn.addEventListener("click", clearAllSeries);
refreshBtn.addEventListener("click", loadData);
alertForm.addEventListener("submit", submitAlert);

loadData();