// URL base da API (ajuste se hospedar em outro lugar)
const API_BASE_URL = "http://127.0.0.1:8000";

let myChart = null;

// Espera o DOM carregar completamente
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("analyzeBtn");
  const input = document.getElementById("tickerInput");

  // Acionar no clique
  btn.addEventListener("click", analyzeStock);

  // Acionar ao apertar Enter
  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") analyzeStock();
  });
});

async function analyzeStock() {
  const tickerInput = document.getElementById("tickerInput");
  const ticker = tickerInput.value.toUpperCase().trim();

  if (!ticker) {
    alert("Por favor, digite um código de ação (ex: VALE3)");
    return;
  }

  // Controle de UI
  const loadingDiv = document.getElementById("loading");
  const resultDiv = document.getElementById("resultArea");

  loadingDiv.classList.remove("hidden");
  resultDiv.classList.add("hidden");

  try {
    // Passo 1: Solicitar ao backend para sincronizar os dados
    const syncResponse = await fetch(`${API_BASE_URL}/sync/${ticker}`, {
      method: "POST",
    });

    if (!syncResponse.ok) {
      throw new Error(`Falha ao sincronizar dados: ${syncResponse.statusText}`);
    }

    // Passo 2: Solicitar análise e previsão
    const analysisResponse = await fetch(`${API_BASE_URL}/analyze/${ticker}`);

    if (!analysisResponse.ok) {
      throw new Error("Erro ao gerar análise da IA");
    }

    const data = await analysisResponse.json();

    // Passo 3: Preencher a tela
    updateDashboard(data, ticker);

    resultDiv.classList.remove("hidden");
  } catch (error) {
    console.error(error);
    alert(`Ocorreu um erro: ${error.message}`);
  } finally {
    loadingDiv.classList.add("hidden");
  }
}

function updateDashboard(data, ticker) {
  // Atualiza Textos
  const signalEl = document.getElementById("aiSignal");
  signalEl.innerText = data.ai_recommendation;

  // Muda cor dinamicamente baseada na recomendação
  if (data.ai_recommendation.includes("COMPRA")) {
    signalEl.className = "text-3xl font-bold mt-2 text-green-500";
  } else {
    signalEl.className = "text-3xl font-bold mt-2 text-red-500";
  }

  document.getElementById("aiConf").innerText = data.ai_confidence;
  document.getElementById("aiAcc").innerText = data.model_accuracy;

  // Formata moeda (R$)
  const priceFormatted = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(data.current_price);
  document.getElementById("currPrice").innerText = priceFormatted;

  // Renderiza Gráfico
  renderChart(data.chart_data.dates, data.chart_data.prices, ticker);
}

function renderChart(dates, prices, ticker) {
  const ctx = document.getElementById("stockChart").getContext("2d");

  // Se já existe um gráfico, destrua-o antes de criar o novo
  if (myChart) {
    myChart.destroy();
  }

  myChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates, // Datas no eixo X
      datasets: [
        {
          label: `Histórico de Fechamento - ${ticker}`,
          data: prices, // Preços no eixo Y
          borderColor: "#34D399", // Verde Tailwind
          backgroundColor: (context) => {
            const ctx = context.chart.ctx;
            const gradient = ctx.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, "rgba(52, 211, 153, 0.5)");
            gradient.addColorStop(1, "rgba(52, 211, 153, 0.0)");
            return gradient;
          },
          borderWidth: 2,
          pointRadius: 0, // Remove bolinhas dos pontos para ficar mais limpo
          pointHoverRadius: 5,
          fill: true,
          tension: 0.1, // Suavização da linha
        },
      ],
    },
    options: {
      responsive: true,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: { labels: { color: "white" } },
        tooltip: { mode: "index", intersect: false },
      },
      scales: {
        x: {
          ticks: { color: "#9CA3AF", maxTicksLimit: 10 },
          grid: { color: "#374151" },
        },
        y: {
          ticks: { color: "#9CA3AF" },
          grid: { color: "#374151" },
        },
      },
    },
  });
}
