import Chart from 'chart.js/auto';

// Interfaces pour typer nos données
interface GasData {
  region: string;
  brands: {
    [brand: string]: {
      gazole_moy: number | null;
      sp95_moy: number | null;
      stations_count: number;
    };
  };
}

interface BrentData {
  price_usd: number;
}

// Couleurs associées aux marques pour plus de lisibilité
const brandColors: Record<string, string> = {
  'Total': '#ff0000',          // Rouge pur
  'Esso': '#ff6b6b',           // Rouge clair / Corail
  'Auchan': '#a30000',         // Rouge très sombre
  'Avia': '#ff007f',           // Rouge rosé / Rose vif
  'Leclerc': '#00a8ff',        // Bleu ciel / clair
  'Carrefour': '#002060',      // Bleu nuit / très foncé
  'Système U': '#00bcd4',      // Bleu cyan / turquoise
  'Intermarché': '#ff9800',    // Orange
  'BP': '#009900',             // Vert
  'Shell': '#ffc107',          // Jaune moutarde
  'Autre': '#9e9e9e'           // Gris
};

function getColorForBrand(brand: string): string {
  if (brandColors[brand]) return brandColors[brand];
  
  // Hash string into a consistent color
  let hash = 0;
  for (let i = 0; i < brand.length; i++) {
    hash = brand.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  // Generate HSL to ensure distinct, vibrant colors
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 70%, 50%)`;
}

async function loadData() {
  const [gasRes, brentRes] = await Promise.all([
    fetch('./gas_prices.json'),
    fetch('./brent_prices.json')
  ]);
  
  const gasPrices: Record<string, GasData> = await gasRes.json();
  const brentPrices: Record<string, BrentData> = await brentRes.json();
  
  return { gasPrices, brentPrices };
}

function calculateVariation(data: (number|null)[], dates: string[], daysAgo: number): string {
  if (data.length === 0) return '-';
  
  // Find the last actual non-null value and its date
  let lastValidIndex = -1;
  for (let i = data.length - 1; i >= 0; i--) {
    if (data[i] !== null) {
      lastValidIndex = i;
      break;
    }
  }
  
  if (lastValidIndex === -1) return '-';
  
  const lastVal = data[lastValidIndex] as number;
  const lastDate = new Date(dates[lastValidIndex]);
  const targetDate = new Date(lastDate);
  targetDate.setDate(targetDate.getDate() - daysAgo);

  let closestIndex = -1;
  let minDiff = Infinity;
  for (let i = 0; i <= lastValidIndex; i++) {
    if (data[i] === null) continue;
    const d = new Date(dates[i]);
    const diff = Math.abs(d.getTime() - targetDate.getTime());
    if (diff < minDiff) {
      minDiff = diff;
      closestIndex = i;
    }
  }

  if (closestIndex === -1 || closestIndex === lastValidIndex) return '-';
  
  const startVal = data[closestIndex];
  if (startVal === null || startVal === 0) return '-';

  const variation = ((lastVal - startVal) / startVal) * 100;
  const sign = variation > 0 ? '+' : '';
  const colorClass = variation > 0 ? 'val-up' : (variation < 0 ? 'val-down' : 'val-neutral');
  return `<span class="${colorClass}">${sign}${variation.toFixed(2)}%</span>`;
}

function updateTable(dates: string[], brentData: (number|null)[], allBrands: Set<string>, gasPrices: Record<string, GasData>, currentFuelType: 'gazole_moy' | 'sp95_moy') {
  const tbody = document.querySelector('#variation-table tbody');
  const tableContainer = document.getElementById('table-container');
  if (!tbody || !tableContainer) return;
  
  tableContainer.style.display = 'block';
  tbody.innerHTML = '';

  const createRow = (name: string, data: (number|null)[]) => {
    const tr = document.createElement('tr');
    const tdName = document.createElement('td');
    tdName.textContent = name;
    tdName.style.fontWeight = 'bold';
    tr.appendChild(tdName);

    const td7 = document.createElement('td');
    td7.innerHTML = calculateVariation(data, dates, 7);
    tr.appendChild(td7);

    const td14 = document.createElement('td');
    td14.innerHTML = calculateVariation(data, dates, 14);
    tr.appendChild(td14);

    const td30 = document.createElement('td');
    td30.innerHTML = calculateVariation(data, dates, 30);
    tr.appendChild(td30);

    return tr;
  };

  tbody.appendChild(createRow('Prix du baril (Brent)', brentData));

  // Sort brands alphabetically
  Array.from(allBrands).sort().forEach(brand => {
    const brandData = dates.map(date => {
        const dayData = gasPrices[date];
        if (dayData && dayData.brands && dayData.brands[brand]) {
          return dayData.brands[brand][currentFuelType];
        }
        return null;
    });
    tbody.appendChild(createRow(brand, brandData));
  });
}

async function renderChart() {
  const { gasPrices, brentPrices } = await loadData();
  
  // Extraire les dates communes et trier
  const dates = Array.from(new Set([...Object.keys(gasPrices), ...Object.keys(brentPrices)])).sort();
  
  // Mise à jour de la date d'affichage
  const lastUpdateSpan = document.getElementById('last-update');
  if (lastUpdateSpan && dates.length > 0) {
    lastUpdateSpan.textContent = dates[dates.length - 1];
  }
  
  // Taux de conversion approximatif pour l'exemple (EUR/USD)
  // 1 baril = 158.98 litres
  const eurUsdRate = 0.94; // 1 USD = 0.94 EUR environ en avril 2026
  
  // Préparer les données du Brent en EUR/Litre
  const brentEurLiter = dates.map(date => {
    const data = brentPrices[date];
    if (!data) return null;
    return (data.price_usd * eurUsdRate) / 158.98;
  });

  // Identifier les marques disponibles
  const allBrands = new Set<string>();
  Object.values(gasPrices).forEach(dayData => {
    if (dayData.brands) {
      Object.keys(dayData.brands).forEach(b => allBrands.add(b));
    }
  });

  const ctx = document.getElementById('priceChart') as HTMLCanvasElement;
  let currentChart: Chart | null = null;
  let currentFuelType: 'gazole_moy' | 'sp95_moy' = 'gazole_moy';
  let currentViewMode: 'absolute' | 'base100' = 'base100';

  const updateChart = () => {
    if (currentChart) {
      currentChart.destroy();
    }

    const datasets: any[] = [];

    // Dataset Brent
    let brentDataToUse = [...brentEurLiter];
    if (currentViewMode === 'base100') {
      const firstVal = brentDataToUse.find(v => v !== null);
      if (firstVal) {
        brentDataToUse = brentDataToUse.map(v => v !== null ? (v / firstVal) * 100 : null);
      }
    }

    datasets.push({
      label: currentViewMode === 'base100' ? 'Prix du baril (Indice 100)' : 'Prix du baril',
      data: brentDataToUse,
      borderColor: '#000000',
      backgroundColor: '#000000',
      borderWidth: 3,
      fill: false,
      tension: 0.2,
      spanGaps: true,
      yAxisID: 'y'
    });

    // Datasets Distributeurs
    allBrands.forEach(brand => {
      let data = dates.map(date => {
        const dayData = gasPrices[date];
        if (dayData && dayData.brands && dayData.brands[brand]) {
          return dayData.brands[brand][currentFuelType];
        }
        return null;
      });

      if (data.some(val => val !== null)) {
        if (currentViewMode === 'base100') {
          const firstVal = data.find(v => v !== null);
          if (firstVal) {
            data = data.map(v => v !== null ? (v / firstVal) * 100 : null);
          }
        }

        datasets.push({
          label: brand,
          data: data,
          borderColor: getColorForBrand(brand),
          backgroundColor: getColorForBrand(brand),
          borderWidth: 2,
          tension: 0.4,
          pointRadius: 0,
          pointHitRadius: 10,
          spanGaps: true,
          yAxisID: currentViewMode === 'absolute' ? 'y1' : 'y'
        });
      }
    });

    updateTable(dates, brentEurLiter, allBrands, gasPrices, currentFuelType);

    currentChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: dates,
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          title: {
            display: true,
            text: `Évolution des prix - ${currentFuelType === 'gazole_moy' ? 'Gazole' : 'SP95'}`,
            font: { size: 16 }
          },
          legend: {
            position: 'bottom',
            labels: {
              boxWidth: 15,
              padding: 10
            }
          },
          tooltip: {
            callbacks: {
              label: function(context: any) {
                let label = context.dataset.label || '';
                if (label) label += ': ';
                if (context.parsed.y !== null) {
                  label += currentViewMode === 'base100' 
                    ? context.parsed.y.toFixed(2) + ' %'
                    : context.parsed.y.toFixed(3) + ' €/L';
                }
                return label;
              }
            }
          }
        },
        scales: {
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: currentViewMode === 'base100' ? 'Indice (Base 100 au 1er Janvier)' : 'Prix Brut (€/L)'
            }
          },
          y1: {
            type: 'linear',
            display: currentViewMode === 'absolute',
            position: 'right',
            title: {
              display: true,
              text: 'Prix Pompe (€/L)'
            },
            grid: {
              drawOnChartArea: false,
            }
          }
        }
      }
    });
  };

  // Initialisation
  updateChart();

  // Gestion des sélecteurs
  const fuelSelector = document.getElementById('fuel-selector') as HTMLSelectElement;
  const viewSelector = document.getElementById('view-selector') as HTMLSelectElement;

  if (fuelSelector) {
    fuelSelector.addEventListener('change', (e) => {
      currentFuelType = (e.target as HTMLSelectElement).value as 'gazole_moy' | 'sp95_moy';
      updateChart();
    });
  }
  
  if (viewSelector) {
    viewSelector.addEventListener('change', (e) => {
      currentViewMode = (e.target as HTMLSelectElement).value as 'absolute' | 'base100';
      updateChart();
    });
  }
}

renderChart();
