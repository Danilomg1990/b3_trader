// Configuração da URL da API (Backend local)
const API_BASE_URL = "http://127.0.0.1:8000";

let myChart = null; // Variável global para guardar a instância do gráfico

// Inicialização: Aguarda o DOM carregar
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("analyzeBtn");
  const input = document.getElementById("tickerInput");

  // Event Listeners
  btn.addEventListener("click", analyzeStock);

  // Permite apertar Enter no input para buscar
  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") analyzeStock();
  });
});

async function analyzeStock() {
  // 1. Coleta de dados do usuário
  const tickerInput = document.getElementById("tickerInput");
  const daysInput = document.getElementById("daysInput");

  const ticker = tickerInput.value.toUpperCase().trim();
  const days = daysInput.value;

  // Validação simples
  if (!ticker) {
    alert("Por favor, digite o código da ação (ex: PETR4, VALE3).");
    return;
  }

  // 2. Controle de Interface (Loading)
  const loadingDiv = document.getElementById("loading");
  const resultDiv = document.getElementById("resultArea");

  loadingDiv.classList.remove("hidden"); // Mostra spinner
  resultDiv.classList.add("hidden"); // Esconde resultados antigos

  try {
    // 3. Passo A: Sincronizar dados (Ingestão + Auditoria)
    // Isso força o backend a baixar dados novos e checar se errou previsões passadas
    const syncResponse = await fetch(`${API_BASE_URL}/sync/${ticker}`, {
      method: "POST",
    });

    if (!syncResponse.ok)
      throw new Error("Erro ao sincronizar dados com a B3.");

    // 4. Passo B: Analisar (Classificação + Regressão)
    const analyzeResponse = await fetch(
      `${API_BASE_URL}/analyze/${ticker}?days=${days}`
    );

    if (!analyzeResponse.ok)
      throw new Error("Erro ao processar inteligência artificial.");

    const data = await analyzeResponse.json();

    // 5. Atualizar a tela com os dados recebidos
    updateDashboard(data, days);

    // Mostra a div de resultados com animação
    resultDiv.classList.remove("hidden");
  } catch (error) {
    console.error("Erro na aplicação:", error);
    alert(`Ocorreu um erro: ${error.message}`);
  } finally {
    // Sempre esconde o loading, dando erro ou não
    loadingDiv.classList.add("hidden");
  }
}

function updateDashboard(data, days) {
  // Formatador de Moeda (R$)
  const fmt = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  });

  // --- Card 1: Sinal da IA ---
  const signalEl = document.getElementById("aiSignal");
  signalEl.innerText = data.signal;

  // Lógica de cores para Compra/Venda
  if (data.signal.includes("COMPRA")) {
    signalEl.className =
      "text-3xl font-bold mt-2 text-green-400 drop-shadow-md";
  } else {
    signalEl.className = "text-3xl font-bold mt-2 text-red-500 drop-shadow-md";
  }
  document.getElementById("aiConf").innerText = data.confidence;

  // --- Card 2: Preço Atual ---
  document.getElementById("currPrice").innerText = fmt.format(
    data.current_price
  );

  // --- Card 3: Previsão de Preço ---
  document.getElementById("targetDays").innerText = days;
  document.getElementById("predPrice").innerText = fmt.format(
    data.predicted_price
  );

  const varEl = document.getElementById("predVar");
  // Adiciona setinha para cima ou para baixo
  const arrow = data.variation_pct > 0 ? "▲" : "▼";
  varEl.innerText = `${arrow} ${data.variation_pct}% (esperado)`;

  // Cor da variação
  varEl.className =
    data.variation_pct > 0
      ? "text-sm font-bold mt-2 text-green-400"
      : "text-sm font-bold mt-2 text-red-400";

  // --- Card 4: Histórico de Auditoria ---
  const historyListEl = document.getElementById("historyList");
  historyListEl.innerHTML = ""; // Limpa lista anterior

  if (data.history && data.history.length > 0) {
    // Mapeia o histórico para HTML
    data.history.forEach((item) => {
      const row = document.createElement("div");
      row.className =
        "flex justify-between items-center border-b border-gray-700 pb-1 mb-1 last:border-0";

      // Ícone de resultado (Check ou X)
      const resultIcon = item.result.includes("✅")
        ? '<span class="text-green-500">✅</span>'
        : '<span class="text-red-500">❌</span>';

      row.innerHTML = `
                <span class="text-gray-400">${item.date}</span>
                <span class="text-blue-300 font-mono">🎯 ${item.predicted.toFixed(
                  2
                )}</span>
                <span>${resultIcon}</span>
            `;
      historyListEl.appendChild(row);
    });
  } else {
    historyListEl.innerHTML =
      '<p class="text-gray-500 italic mt-2">Nenhuma previsão auditada ainda.</p>';
  }

  // --- Gráfico ---
  renderChart(data.chart_data.dates, data.chart_data.prices, data.ticker);
}

function renderChart(dates, prices, ticker) {
  const ctx = document.getElementById("stockChart").getContext("2d");

  // Destrói gráfico antigo para evitar sobreposição/flickering
  if (myChart) {
    myChart.destroy();
  }

  // Cria gradiente bonito para o gráfico
  const gradient = ctx.createLinearGradient(0, 0, 0, 400);
  gradient.addColorStop(0, "rgba(16, 185, 129, 0.5)"); // Verde forte no topo
  gradient.addColorStop(1, "rgba(16, 185, 129, 0.0)"); // Transparente embaixo

  myChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        {
          label: `Histórico ${ticker}`,
          data: prices,
          borderColor: "#10B981", // Emerald-500
          backgroundColor: gradient,
          borderWidth: 2,
          pointRadius: 0, // Remove bolinhas para visual limpo
          pointHoverRadius: 6, // Mostra bolinha ao passar mouse
          fill: true,
          tension: 0.1, // Suavização da curva
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: { labels: { color: "#D1D5DB" } }, // Cor da legenda
        tooltip: {
          backgroundColor: "rgba(17, 24, 39, 0.9)",
          titleColor: "#34D399",
          bodyColor: "#fff",
          borderColor: "#374151",
          borderWidth: 1,
        },
      },
      scales: {
        x: {
          ticks: { color: "#9CA3AF", maxTicksLimit: 8 },
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
