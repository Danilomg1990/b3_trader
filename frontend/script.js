// Configuração da URL da API
const API_BASE_URL = "http://127.0.0.1:8000";

let chart = null;
let progressInterval = null; // Variável para controlar a animação da barra

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("analyzeBtn");
  const input = document.getElementById("tickerInput");

  btn.addEventListener("click", analyzeStock);
  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") analyzeStock();
  });
});

async function analyzeStock() {
  const tickerInput = document.getElementById("tickerInput");
  const daysInput = document.getElementById("daysInput");
  const timeframeInput = document.getElementById("timeframeInput");
  const chartTypeInput = document.getElementById("chartTypeInput");

  const ticker = tickerInput.value.toUpperCase().trim();
  const days = daysInput.value;
  const timeframe = timeframeInput.value;
  const chartType = chartTypeInput.value;

  const checkboxes = document.querySelectorAll(
    'input[name="indicators"]:checked'
  );
  let selectedIndicators = [];
  checkboxes.forEach((c) => selectedIndicators.push(c.value));

  if (!ticker) {
    alert("Digite o código da ação!");
    return;
  }

  // --- INÍCIO DO LOADING ---
  const loadingDiv = document.getElementById("loading");
  const resultDiv = document.getElementById("resultArea");

  loadingDiv.classList.remove("hidden");
  resultDiv.classList.add("hidden");

  // Inicia a Animação da Barra
  startProgressBar();

  try {
    // Passo 1: Sync (Dados)
    await fetch(`${API_BASE_URL}/sync/${ticker}`, { method: "POST" });

    // Passo 2: Analyze (IA)
    const params = new URLSearchParams();
    params.append("days", days);
    params.append("timeframe", timeframe);
    selectedIndicators.forEach((ind) => params.append("indicators", ind));

    const res = await fetch(
      `${API_BASE_URL}/analyze/${ticker}?${params.toString()}`
    );
    if (!res.ok) throw new Error("Erro na IA ou dados insuficientes");

    const data = await res.json();

    // --- SUCESSO ---
    finishProgressBar(); // Enche a barra até 100%

    // Pequeno delay para o usuário ver o 100% antes de mostrar o resultado
    setTimeout(() => {
      updateDashboard(data, days, timeframe, chartType);
      loadingDiv.classList.add("hidden");
      resultDiv.classList.remove("hidden");
    }, 600);
  } catch (error) {
    console.error(error);
    alert(error.message);
    loadingDiv.classList.add("hidden");
    stopProgressBar(); // Reseta se der erro
  }
}

// --- FUNÇÕES DA BARRA DE PROGRESSO ---

function startProgressBar() {
  const bar = document.getElementById("loadingBar");
  const text = document.getElementById("loadingText");
  let width = 0;

  // Reseta estado inicial
  bar.style.width = "0%";
  text.innerText = "Iniciando conexão...";

  // Limpa intervalo anterior se existir
  if (progressInterval) clearInterval(progressInterval);

  progressInterval = setInterval(() => {
    // Aumenta a barra de forma aleatória para parecer natural
    if (width < 90) {
      width += Math.random() * 5;
      if (width > 90) width = 90; // Trava em 90% até o servidor responder

      bar.style.width = width + "%";

      // Muda o texto baseado no progresso
      if (width > 10 && width < 40) text.innerText = "Baixando Histórico B3...";
      else if (width >= 40 && width < 70)
        text.innerText = "Calculando Indicadores Institucionais...";
      else if (width >= 70)
        text.innerText = "Executando Ensemble Neural (IA)...";
    }
  }, 200); // Atualiza a cada 200ms
}

function finishProgressBar() {
  if (progressInterval) clearInterval(progressInterval);
  const bar = document.getElementById("loadingBar");
  const text = document.getElementById("loadingText");

  bar.style.width = "100%";
  text.innerText = "Análise Concluída! 🚀";
}

function stopProgressBar() {
  if (progressInterval) clearInterval(progressInterval);
}

// --- FUNÇÕES DE DASHBOARD E GRÁFICO (Mantidas iguais) ---

function updateDashboard(data, days, timeframe, chartType) {
  const fmt = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  });

  const signalEl = document.getElementById("aiSignal");
  signalEl.innerText = data.signal;

  if (data.signal.includes("COMPRA"))
    signalEl.className =
      "text-3xl font-bold mt-2 text-green-400 drop-shadow-md";
  else if (data.signal.includes("VENDA"))
    signalEl.className = "text-3xl font-bold mt-2 text-red-500 drop-shadow-md";
  else signalEl.className = "text-3xl font-bold mt-2 text-gray-400";

  document.getElementById("aiConf").innerText = data.confidence;
  document.getElementById("currPrice").innerText = fmt.format(
    data.current_price
  );

  let timeLabel =
    timeframe === "D"
      ? "dias"
      : timeframe === "W"
      ? "semanas"
      : timeframe === "M"
      ? "meses"
      : "anos";
  document.getElementById("targetDays").innerText = days;
  document.getElementById("targetTimeframeLabel").innerText = timeLabel;
  document.getElementById("predPrice").innerText = fmt.format(
    data.predicted_price
  );

  const varEl = document.getElementById("predVar");
  const arrow = data.variation_pct > 0 ? "▲" : "▼";
  varEl.innerText = `${arrow} ${data.variation_pct.toFixed(2)}%`;
  varEl.className =
    data.variation_pct > 0
      ? "text-sm font-bold mt-2 text-green-400"
      : "text-sm font-bold mt-2 text-red-400";

  document.getElementById("historyList").innerHTML =
    '<p class="text-gray-500 italic">Gráfico atualizado.</p>';

  renderApexChart(data.chart_data, data.ticker, chartType);
}

function renderApexChart(chartData, ticker, chartType) {
  if (chart) chart.destroy();

  const cleanCandles = chartData.candles.map((c) => ({
    x: c.x,
    y: [
      parseFloat(c.y[0].toFixed(2)),
      parseFloat(c.y[1].toFixed(2)),
      parseFloat(c.y[2].toFixed(2)),
      parseFloat(c.y[3].toFixed(2)),
    ],
  }));

  // Função segura para mapear indicadores
  const mapSafe = (arr) =>
    arr
      ? arr.map((p) => ({ x: p.x, y: p.y ? parseFloat(p.y.toFixed(2)) : null }))
      : [];

  const cleanVWAP = mapSafe(chartData.vwap);
  const cleanBBU = mapSafe(chartData.bb_upper);
  const cleanBBL = mapSafe(chartData.bb_lower);
  const cleanSMA14 = mapSafe(chartData.sma_14);
  const cleanSMA50 = mapSafe(chartData.sma_50);

  let mainSeries = {};
  if (chartType === "candlestick") {
    mainSeries = { name: "Preço", type: "candlestick", data: cleanCandles };
  } else {
    const lineData = cleanCandles.map((c) => ({ x: c.x, y: c.y[3] }));
    mainSeries = { name: "Preço", type: "area", data: lineData };
  }

  const options = {
    series: [
      mainSeries,
      { name: "VWAP", type: "line", data: cleanVWAP },
      { name: "SMA 14", type: "line", data: cleanSMA14 },
      { name: "SMA 50", type: "line", data: cleanSMA50 },
      { name: "BB Upper", type: "line", data: cleanBBU },
      { name: "BB Lower", type: "line", data: cleanBBL },
    ],
    chart: {
      type: chartType === "candlestick" ? "candlestick" : "line",
      height: 500,
      background: "#1F2937",
      toolbar: { show: true },
      animations: { enabled: true },
    },
    title: {
      text: `${ticker} - Análise Quantitativa`,
      align: "left",
      style: { color: "#fff", fontSize: "16px" },
    },
    stroke: {
      width: [chartType === "candlestick" ? 1 : 2, 2, 2, 2, 1, 1],
      curve: "smooth",
      dashArray: [0, 5, 0, 0, 0, 0],
    },
    colors: [
      chartType === "candlestick" ? "#00E396" : "#2E93fA",
      "#FEB019",
      "#EC4899",
      "#3B82F6",
      "#775DD0",
      "#775DD0",
    ],
    fill: {
      type: [
        chartType === "candlestick" ? "solid" : "gradient",
        "solid",
        "solid",
        "solid",
        "solid",
        "solid",
      ],
      gradient: {
        shadeIntensity: 1,
        opacityFrom: 0.5,
        opacityTo: 0.05,
        stops: [0, 100],
      },
    },
    xaxis: {
      type: "datetime",
      labels: { style: { colors: "#9CA3AF" } },
      tooltip: { enabled: true },
    },
    yaxis: {
      tooltip: { enabled: true },
      labels: {
        style: { colors: "#9CA3AF" },
        formatter: (val) => {
          return val ? val.toFixed(2) : val;
        },
      },
    },
    grid: { borderColor: "#374151", strokeDashArray: 4 },
    theme: { mode: "dark" },
    tooltip: {
      theme: "dark",
      shared: true,
      intersect: false,
      y: {
        formatter: function (val) {
          return val ? "R$ " + val.toFixed(2) : val;
        },
      },
    },
    plotOptions: {
      candlestick: { colors: { upward: "#00E396", downward: "#FF4560" } },
    },
  };

  chart = new ApexCharts(document.querySelector("#stockChart"), options);
  chart.render();
}
