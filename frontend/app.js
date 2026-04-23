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
  return [...new Set(items.map(item => item[key]))].sort((a, b) => a.localeCompare(b, "th"));
}

function buildSeriesKey(retailer, oilType) {
  return `${retailer}__${oilType}`;
}

function parseSeriesKey(key) {
  const [retailer, oilType] = key.split("__");
  return { retailer, oilType };
}

function formatOilTypeLabel(oilType) {
  return (oilType || "").replace(/_/g, " ");
}

function getSeriesLabel(series) {
  return `${series.retailer} - ${formatOilTypeLabel(series.oilType)}`;
}

function getSeriesByKey(key) {
  const { retailer, oilType } = parseSeriesKey(key);
  return allHistory.find(item => item.retailer === retailer && item.oilType === oilType);
}

function setSelectOptions(selectElement, values, formatter = value => value) {
  selectElement.innerHTML = "";

  if (!values.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No data available";
    selectElement.appendChild(option);
    selectElement.disabled = true;
    return;
  }

  selectElement.disabled = false;

  values.forEach(value => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = formatter(value);
    selectElement.appendChild(option);
  });
}

function updateOilTypesDropdown(retailerSelectElem, oilTypeSelectElem) {
  const selectedRetailer = retailerSelectElem.value;
  const retailerData = allHistory.filter(item => item.retailer === selectedRetailer);
  const availableOilTypes = uniqueValues(retailerData, "oilType");
  setSelectOptions(oilTypeSelectElem, availableOilTypes, formatOilTypeLabel);
}

function populateControls() {
  const retailers = uniqueValues(allHistory, "retailer");

  setSelectOptions(retailerSelect, retailers);
  setSelectOptions(alertRetailerSelect, retailers);

  if (retailers.length > 0) {
    updateOilTypesDropdown(retailerSelect, oilTypeSelect);
    updateOilTypesDropdown(alertRetailerSelect, alertOilTypeSelect);
  } else {
    setSelectOptions(oilTypeSelect, [], formatOilTypeLabel);
    setSelectOptions(alertOilTypeSelect, [], formatOilTypeLabel);
  }
}

function getLatestItems() {
  return allHistory
    .map(series => {
      const latestPoint = series.points[series.points.length - 1];
      if (!latestPoint) {
        return null;
      }

      return {
        retailer: series.retailer,
        oilType: series.oilType,
        price: Number(latestPoint.price),
        updatedAt: latestPoint.time
      };
    })
    .filter(Boolean)
    .sort((a, b) => {
      const retailerCompare = a.retailer.localeCompare(b.retailer, "en");
      if (retailerCompare !== 0) {
        return retailerCompare;
      }
      return a.oilType.localeCompare(b.oilType, "th");
    });
}

function getPointDateLabel(point) {
  const raw = point?.time || "";
  return raw.slice(0, 10);
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

  if (!latestItems.length) {
    const row = document.createElement("tr");
    row.innerHTML = `<td colspan="4" class="empty-state">No data available.</td>`;
    latestPriceTableBody.appendChild(row);
    return;
  }

  latestItems.forEach(item => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${item.retailer}</td>
      <td>${formatOilTypeLabel(item.oilType)}</td>
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
      options: { responsive: true, maintainAspectRatio: false }
    });
    chartStatus.textContent = allHistory.length ? "No series selected." : "No data available.";
    return;
  }

  const allDates = selectedSeries.flatMap(series =>
    series.points.map(point => getPointDateLabel(point))
  );

  const labels = [...new Set(allDates)].sort();

  const datasets = selectedSeries.map(series => ({
    label: getSeriesLabel(series),
    data: labels.map(dateLabel => {
      const pointForDate = [...series.points]
        .filter(point => getPointDateLabel(point) === dateLabel)
        .sort((a, b) => (a.time || "").localeCompare(b.time || ""))
        .pop();

      return pointForDate ? pointForDate.price : null;
    }),
    tension: 0.25,
    spanGaps: true
  }));

  chart = new Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "top" } },
      scales: {
        x: { title: { display: true, text: "Date" } },
        y: { title: { display: true, text: "Price (THB/L)" } }
      }
    }
  });

  chartStatus.textContent = `Showing ${selectedSeries.length} selected series.`;
}

function addSelectedSeries() {
  const key = buildSeriesKey(retailerSelect.value, oilTypeSelect.value);

  if (!retailerSelect.value || !oilTypeSelect.value) {
    chartStatus.textContent = "No data available.";
    return;
  }

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
  if (!CONFIG || !CONFIG.API_BASE_URL) {
    throw new Error("CONFIG.API_BASE_URL is not set.");
  }

  const response = await fetch(`${CONFIG.API_BASE_URL}/prices`);
  if (!response.ok) {
    throw new Error(`History request failed with status ${response.status}`);
  }

  const data = await response.json();
  return data.items || [];
}

async function loadData() {
  chartStatus.textContent = "Loading data...";
  backendStatus.textContent = "Connecting...";

  try {
    allHistory = await fetchHistory();

    populateControls();
    renderLatestSummary();
    renderLatestTable();

    selectedSeriesKeys = selectedSeriesKeys.filter(key => Boolean(getSeriesByKey(key)));

    if (!selectedSeriesKeys.length && allHistory.length) {
      selectedSeriesKeys = [buildSeriesKey(allHistory[0].retailer, allHistory[0].oilType)];
    }

    renderSelectedChips();
    renderChart();

    backendStatus.textContent = "Connected";
    if (!allHistory.length) {
      chartStatus.textContent = "Connected, but no historical data is available yet.";
    }
  } catch (error) {
    console.error(error);
    allHistory = [];
    populateControls();
    renderLatestSummary();
    renderLatestTable();
    selectedSeriesKeys = [];
    renderSelectedChips();
    renderChart();
    chartStatus.textContent = "Failed to load data from the API.";
    backendStatus.textContent = "Unavailable";
  }
}

async function submitAlert(event) {
  event.preventDefault();

  if (!CONFIG || !CONFIG.API_BASE_URL) {
    alertResult.className = "alert-box";
    alertResult.textContent = "CONFIG.API_BASE_URL is not set.";
    return;
  }

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
      throw new Error(result.message || result.error || "Failed to create alert");
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
retailerSelect.addEventListener("change", () => updateOilTypesDropdown(retailerSelect, oilTypeSelect));
alertRetailerSelect.addEventListener("change", () => updateOilTypesDropdown(alertRetailerSelect, alertOilTypeSelect));

loadData();
