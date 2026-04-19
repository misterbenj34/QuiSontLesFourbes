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
  'Total': '#ff0000',
  'Leclerc': '#0055a4',
  'Carrefour': '#00387b',
  'Intermarche': '#000000',
  'Auchan': '#e30613',
  'Systeme U': '#005eb8',
  'Bp': '#009900',
  'Esso': '#d32f2f',
  'Shell': '#ffeb3b',
  'Autre': '#9e9e9e'
};

async function loadData() {
  const [gasRes, brentRes] = await Promise.all([
    fetch('./gas_prices.json'),
    fetch('./brent_prices.json')
  ]);
  
  const gasPrices: Record<string, GasData> = await gasRes.json();
  const brentPrices: Record<string, BrentData> = await brentRes.json();
  
  return { gasPrices, brentPrices };
}

async function renderChart() {
  const { gasPrices, brentPrices } = await loadData();
  
  // Extraire les dates communes et trier
  const dates = Array.from(new Set([...Object.keys(gasPrices), ...Object.keys(brentPrices)])).sort();
  
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

  // Création du graphique
  const ctx = document.getElementById('priceChart') as HTMLCanvasElement;
  let currentChart: Chart | null = null;

  const updateChart = (fuelType: 'gazole_moy' | 'sp95_moy') => {
    if (currentChart) {
      currentChart.destroy();
    }

    const datasets: any[] = [];

    // Ajouter le dataset du Brent (Axe de base)
    datasets.push({
      label: 'Brent (Pétrole brut estimé en €/L)',
      data: brentEurLiter,
      borderColor: '#ff9800',
      backgroundColor: 'rgba(255, 152, 0, 0.1)',
      borderWidth: 3,
      fill: true,
      tension: 0.2,
      yAxisID: 'y'
    });

    // Ajouter les datasets pour chaque marque
    allBrands.forEach(brand => {
      const data = dates.map(date => {
        const dayData = gasPrices[date];
        if (dayData && dayData.brands && dayData.brands[brand]) {
          return dayData.brands[brand][fuelType];
        }
        return null;
      });

      // On n'affiche que si on a des données pour cette marque
      if (data.some(val => val !== null)) {
        datasets.push({
          label: `${brand} (${fuelType === 'gazole_moy' ? 'Gazole' : 'SP95'})`,
          data: data,
          borderColor: brandColors[brand] || '#000000',
          borderWidth: 2,
          tension: 0.1,
          spanGaps: true,
          yAxisID: 'y1'
        });
      }
    });

    currentChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: dates,
        datasets: datasets
      },
      options: {
        responsive: true,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        scales: {
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: 'Prix Brut (€/L)'
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            title: {
              display: true,
              text: 'Prix Pompe (€/L)'
            },
            grid: {
              drawOnChartArea: false, // Ne dessine la grille que pour l'axe de gauche
            },
            // On peut aligner les échelles si on veut, mais les prix à la pompe incluent ~60% de taxes
            // Il est donc normal qu'ils soient beaucoup plus élevés (~2.00€ vs ~0.55€ pour le brut)
          }
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: function(context) {
                let label = context.dataset.label || '';
                if (label) {
                  label += ': ';
                }
                if (context.parsed.y !== null) {
                  label += context.parsed.y.toFixed(3) + ' €/L';
                }
                return label;
              }
            }
          }
        }
      }
    });
  };

  // Initialisation sur Gazole
  updateChart('gazole_moy');

  // Gestion du sélecteur
  const fuelSelector = document.getElementById('fuel-selector') as HTMLSelectElement;
  if (fuelSelector) {
    fuelSelector.addEventListener('change', (e) => {
      const value = (e.target as HTMLSelectElement).value as 'gazole_moy' | 'sp95_moy';
      updateChart(value);
    });
  }
}

renderChart();
