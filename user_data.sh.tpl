#!/bin/bash
dnf install -y nginx
cat <<'HTML' > /usr/share/nginx/html/index.html
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Thailand Oil Price Tracker</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-slate-50 font-sans text-slate-800">
  
  <header class="bg-[#0f172a] text-white pt-12 pb-24 px-8 md:px-16">
    <h1 class="text-4xl font-bold mb-3 tracking-tight">Thailand Oil Price Tracker</h1>
    <p class="text-slate-300 text-lg">Compare oil prices over time by retailer and oil type</p>
  </header>

  <main class="max-w-6xl mx-auto -mt-12 px-4 sm:px-6 lg:px-8 mb-12">
    <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-6 md:p-10">
      <h2 class="text-2xl font-bold mb-8">Oil Price Trend</h2>
      
      <div class="flex flex-wrap items-end gap-4 mb-10">
        <div>
          <label class="block text-sm font-medium text-slate-600 mb-2">Retailer</label>
          <select id="retailer" class="bg-white border border-slate-300 text-slate-700 rounded-md px-4 py-2 w-56 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-sm">
            <option value="Bangchak">Bangchak</option>
            <option value="PTT">PTT</option>
            <option value="Shell">Shell</option>
          </select>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-slate-600 mb-2">Oil Type</label>
          <select id="oilType" class="bg-white border border-slate-300 text-slate-700 rounded-md px-4 py-2 w-56 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-sm">
            <option value="Diesel">Diesel</option>
            <option value="Gasohol 95">Gasohol 95</option>
            <option value="Gasohol 91">Gasohol 91</option>
            <option value="Gasohol E20">Gasohol E20</option>
          </select>
        </div>
        
        <button id="addBtn" class="bg-[#2563eb] hover:bg-blue-700 text-white font-medium py-2 px-5 rounded-md transition-colors shadow-sm">
          Add to Graph
        </button>
        
        <button id="clearBtn" class="bg-slate-600 hover:bg-slate-700 text-white font-medium py-2 px-5 rounded-md transition-colors shadow-sm">
          Clear All
        </button>
      </div>

      <div class="relative h-[500px] w-full">
        <canvas id="oilChart"></canvas>
      </div>
    </div>
  </main>

  <script>
    // This uses a SINGLE dollar sign because it is a Terraform variable
    const API_URL = "${api_base_url}/prices";
    
    let chartInstance = null;

    const brandColors = {
        'Bangchak': '#38bdf8',
        'PTT': '#10b981',
        'Shell': '#f59e0b'
    };

    function initChart() {
        const ctx = document.getElementById('oilChart').getContext('2d');
        chartInstance = new Chart(ctx, {
            type: 'line',
            data: { labels: [], datasets: [] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { usePointStyle: true, boxWidth: 8 } }
                },
                scales: {
                    y: {
                        title: { display: true, text: 'Price (THB/L)', color: '#64748b' },
                        grid: { color: '#f1f5f9' },
                        border: { dash: [4, 4] }
                    },
                    x: {
                        title: { display: true, text: 'Time', color: '#64748b' },
                        grid: { color: '#f1f5f9' }
                    }
                }
            }
        });
    }

    async function fetchAndPlot(retailer, oilType) {
        // 1. Create the label we are looking for (using Terraform escaping $$)
        const targetLabel = `$${retailer} - $${oilType}`;

        // 2. Check if this label already exists in the chart's datasets
        const isDuplicate = chartInstance.data.datasets.some(dataset => dataset.label === targetLabel);
        
        if (isDuplicate) {
            alert("This data is already on the graph!");
            return; // Exit the function early to prevent duplicates
        }

        try {
            // These use DOUBLE dollar signs ($$) to escape JavaScript variables from Terraform
            const fetchUrl = `$${API_URL}?retailer=$${encodeURIComponent(retailer)}&type=$${encodeURIComponent(oilType)}`;
            const res = await fetch(fetchUrl);
            const result = await res.json();
            
            const labels = result.data.map(d => new Date(d.timestamp).toLocaleString());
            const prices = result.data.map(d => d.price);

            if (chartInstance.data.labels.length === 0) {
                chartInstance.data.labels = labels;
            }

            // Create different dash patterns: Solid, Dashed, Long-Dashed, Dotted
            const dashPatterns = [[], [5, 5], [10, 5], [2, 2]];
            const currentCount = chartInstance.data.datasets.length;
            const selectedDash = dashPatterns[currentCount % dashPatterns.length];
            
            const newDataset = {
                label: targetLabel, // Use the label we defined above
                data: prices,
                borderColor: brandColors[retailer] || '#64748b',
                backgroundColor: brandColors[retailer] || '#64748b',
                borderWidth: 2,
                borderDash: selectedDash, // Makes overlapping lines visible
                order: -currentCount,     // Negative order forces newer lines to the front layer
                pointBackgroundColor: brandColors[retailer] || '#64748b',
                pointRadius: 4,
                tension: 0.3
            };
            
            chartInstance.data.datasets.push(newDataset);
            chartInstance.update();

        } catch (error) {
            console.error("Error fetching data:", error);
            alert("Failed to load data from the API.");
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        initChart();

        document.getElementById('addBtn').addEventListener('click', () => {
            const retailer = document.getElementById('retailer').value;
            const oilType = document.getElementById('oilType').value;
            fetchAndPlot(retailer, oilType);
        });

        document.getElementById('clearBtn').addEventListener('click', () => {
            chartInstance.data.datasets = [];
            chartInstance.update();
        });
    });
  </script>
</body>
</html>
HTML

systemctl enable --now nginx