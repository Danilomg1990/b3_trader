// Configuração da URL da API (Backend local)
const API_BASE_URL = "http://127.0.0.1:8000";

// Variável global para guardar a instância do gráfico ApexCharts
let chart = null;

// Inicialização: Aguarda o DOM carregar
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("analyzeBtn");
  const input = document.getElementById("tickerInput");

  // Ouve o botão de analisar
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
  const timeframeInput = document.getElementById("timeframeInput");
  const chartTypeInput = document.getElementById("chartTypeInput");

  const ticker = tickerInput.value.toUpperCase().trim();
  const days = daysInput.value;
  const timeframe = timeframeInput.value;
  const chartType = chartTypeInput.value;

  // Captura os Checkboxes marcados (Estratégia)
  const checkboxes = document.querySelectorAll(
    'input[name="indicators"]:checked'
  );
  let selectedIndicators = [];
  checkboxes.forEach((checkbox) => {
    selectedIndicators.push(checkbox.value);
  });

  // Validação
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
    const syncResponse = await fetch(`${API_BASE_URL}/sync/${ticker}`, {
      method: "POST",
    });

    if (!syncResponse.ok) {
      throw new Error("Erro ao sincronizar dados com a B3.");
    }

    // 4. Passo B: Analisar (IA + Ensemble)
    // Montamos a URL com todos os parâmetros
    const params = new URLSearchParams();
    params.append("days", days);
    params.append("timeframe", timeframe);
    selectedIndicators.forEach((ind) => params.append("indicators", ind));

    const analyzeResponse = await fetch(
      `${API_BASE_URL}/analyze/${ticker}?${params.toString()}`
    );

    if (!analyzeResponse.ok) {
      throw new Error("Erro ao processar inteligência artificial.");
    }

    const data = await analyzeResponse.json();

    // 5. Atualizar a tela e renderizar o gráfico
    updateDashboard(data, days, timeframe, chartType);

    // Mostra a div de resultados
    resultDiv.classList.remove("hidden");
  } catch (error) {
    console.error("Erro na aplicação:", error);
    alert(`Ocorreu um erro: ${error.message}`);
  } finally {
    // Sempre esconde o loading
    loadingDiv.classList.add("hidden");
  }
}

function updateDashboard(data, days, timeframe, chartType) {
  // Formatador de Moeda (R$)
  const fmt = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  });

  // --- Atualiza os Cards Superiores ---

  // 1. Sinal da IA
  const signalEl = document.getElementById("aiSignal");
  signalEl.innerText = data.signal;

  // Cores do Sinal
  if (data.signal.includes("COMPRA")) {
    signalEl.className =
      "text-3xl font-bold mt-2 text-green-400 drop-shadow-md";
  } else if (data.signal.includes("VENDA")) {
    signalEl.className = "text-3xl font-bold mt-2 text-red-500 drop-shadow-md";
  } else {
    signalEl.className = "text-3xl font-bold mt-2 text-gray-400";
  }
  document.getElementById("aiConf").innerText = data.confidence;

  // 2. Preço Atual
  document.getElementById("currPrice").innerText = fmt.format(
    data.current_price
  );

  // 3. Previsão (Alvo)
  // Ajusta o texto do prazo (dias, semanas, etc)
  let timeLabel = "dias";
  if (timeframe === "W") timeLabel = "semanas";
  if (timeframe === "M") timeLabel = "meses";
  if (timeframe === "Y") timeLabel = "anos";

  document.getElementById("targetDays").innerText = days;
  document.getElementById("targetTimeframeLabel").innerText = timeLabel;
  document.getElementById("predPrice").innerText = fmt.format(
    data.predicted_price
  );

  const varEl = document.getElementById("predVar");
  const arrow = data.variation_pct > 0 ? "▲" : "▼";
  varEl.innerText = `${arrow} ${data.variation_pct.toFixed(2)}% (esperado)`;

  varEl.className =
    data.variation_pct > 0
      ? "text-sm font-bold mt-2 text-green-400"
      : "text-sm font-bold mt-2 text-red-400";

  // 4. Histórico (Placeholder)
  const historyListEl = document.getElementById("historyList");
  historyListEl.innerHTML =
    '<p class="text-gray-500 italic mt-2">Dados atualizados no gráfico.</p>';

  // --- Renderiza o Gráfico Profissional (ApexCharts) ---
  renderApexChart(data.chart_data, data.ticker, chartType);
}

function renderApexChart(chartData, ticker, chartType) {
  // Se já existe um gráfico, destrói para criar um novo limpo
  if (chart) {
    chart.destroy();
  }

  // PREPARAÇÃO DOS DADOS
  // O ApexCharts precisa de séries separadas.
  // Se o usuário escolheu 'candlestick', usamos os dados OHLC.
  // Se escolheu 'area' (linha), extraímos apenas o preço de Fechamento.

  let mainSeries = {};

  if (chartType === "candlestick") {
    mainSeries = {
      name: "Preço",
      type: "candlestick",
      data: chartData.candles,
    };
  } else {
    // Mapeia os candles para pegar apenas o fechamento (índice 3 do array y: [Open, High, Low, Close])
    const lineData = chartData.candles.map((c) => ({
      x: c.x,
      y: c.y[3], // Pega o Close
    }));

    mainSeries = {
      name: "Preço",
      type: "area", // 'area' cria aquele efeito bonito com degradê embaixo da linha
      data: lineData,
    };
  }

  // CONFIGURAÇÃO DO GRÁFICO (OPÇÕES)
  const options = {
    series: [
      mainSeries, // Série Principal (Vela ou Linha)
      {
        name: "VWAP",
        type: "line",
        data: chartData.vwap,
      },
      {
        name: "BB Upper",
        type: "line",
        data: chartData.bb_upper,
      },
      {
        name: "BB Lower",
        type: "line",
        data: chartData.bb_lower,
      },
    ],
    chart: {
      // O tipo base do gráfico muda conforme a seleção para ajustar comportamentos internos
      type: chartType === "candlestick" ? "candlestick" : "line",
      height: 500,
      background: "#1F2937", // Fundo Dark (Gray-800 do Tailwind)
      toolbar: {
        show: true,
        tools: {
          download: true,
          selection: true,
          zoom: true,
          zoomin: true,
          zoomout: true,
          pan: true,
          reset: true,
        },
      },
      animations: {
        enabled: true,
      },
    },
    title: {
      text: `${ticker} - Análise Quantitativa`,
      align: "left",
      style: {
        color: "#fff",
        fontSize: "16px",
        fontFamily: "sans-serif",
      },
    },
    // Estilo das Linhas
    stroke: {
      // Define a espessura: [Principal, VWAP, BBUpper, BBLower]
      // Se for Candle, a linha principal é 1px (contorno). Se for Linha, é 2px.
      width: [chartType === "candlestick" ? 1 : 2, 2, 1, 1],
      curve: "smooth", // Suaviza as linhas de médias
      dashArray: [0, 5, 0, 0], // VWAP tracejada (5px linha, 5px espaço)
    },
    // Cores das Séries
    colors: [
      chartType === "candlestick" ? "#00E396" : "#2E93fA", // Verde (Candle) ou Azul (Linha)
      "#FEB019", // VWAP Laranja Neon
      "#775DD0", // Bollinger Roxo
      "#775DD0", // Bollinger Roxo
    ],
    // Preenchimento
    fill: {
      // Candle é solido. Area é gradiente. Linhas são solidas.
      type: [
        chartType === "candlestick" ? "solid" : "gradient",
        "solid",
        "solid",
        "solid",
      ],
      gradient: {
        shadeIntensity: 1,
        opacityFrom: 0.5,
        opacityTo: 0.05, // Faz o degradê sumir no final
        stops: [0, 100],
      },
    },
    // Eixo X (Tempo)
    xaxis: {
      type: "datetime",
      labels: {
        style: { colors: "#9CA3AF" }, // Cor do texto (Cinza claro)
      },
      tooltip: {
        enabled: true,
      },
    },
    // Eixo Y (Preço)
    yaxis: {
      tooltip: {
        enabled: true,
      },
      labels: {
        style: { colors: "#9CA3AF" },
        // FORMATAÇÃO IMPORTANTE: Força 2 casas decimais no eixo Y
        formatter: (value) => {
          return value ? value.toFixed(2) : value;
        },
      },
    },
    grid: {
      borderColor: "#374151", // Linhas de grade sutis
      strokeDashArray: 4,
    },
    theme: {
      mode: "dark", // Tema escuro nativo do ApexCharts
    },
    // Tooltip (Caixinha que aparece ao passar o mouse)
    tooltip: {
      theme: "dark",
      shared: true, // Mostra todos os valores juntos
      intersect: false,
      y: {
        // FORMATAÇÃO IMPORTANTE: Força R$ 0,00 no Tooltip
        formatter: function (val) {
          return val ? "R$ " + val.toFixed(2) : val;
        },
      },
    },
    // Configuração Específica para Velas (Cores Brasileiras: Verde/Vermelho)
    plotOptions: {
      candlestick: {
        colors: {
          upward: "#00E396", // Verde Alta
          downward: "#FF4560", // Vermelho Baixa
        },
        wick: {
          useFillColor: true,
        },
      },
    },
  };

  // Cria e renderiza o gráfico na div #stockChart
  chart = new ApexCharts(document.querySelector("#stockChart"), options);
  chart.render();
}
