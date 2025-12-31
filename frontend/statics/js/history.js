// history.js

// URL do Backend
const API_BASE = "http://127.0.0.1:8000";

// Função Principal: Chama as duas APIs ao carregar a página
async function loadData() {
  await loadStats(); // Carrega o Ranking (Topo)
  await loadLog(); // Carrega o Log Detalhado (Baixo)
}

// ======================================================
// 1. CARREGA O RANKING DE ASSERTIVIDADE (Resumo)
// ======================================================
async function loadStats() {
  try {
    const res = await fetch(`${API_BASE}/history/stats`);

    if (!res.ok) throw new Error("Erro ao buscar estatísticas");

    const data = await res.json();
    const tbody = document.getElementById("statsTable");

    // Se não tiver tabela no HTML, para a execução (segurança)
    if (!tbody) return;

    // Se a lista estiver vazia (banco novo)
    if (data.length === 0) {
      tbody.innerHTML = `
                <tr>
                    <td colspan="4" class="px-6 py-8 text-center text-gray-500">
                        Nenhum dado auditado ainda. <br>
                        <span class="text-xs">O sistema precisa que a data alvo passe para conferir o acerto.</span>
                    </td>
                </tr>`;
      return;
    }

    // Gera o HTML
    tbody.innerHTML = data
      .map((item) => {
        // Define cor da porcentagem
        let colorClass = "text-red-400";
        if (item.accuracy >= 50) colorClass = "text-yellow-400";
        if (item.accuracy >= 60) colorClass = "text-green-400";

        return `
            <tr class="hover:bg-gray-700 transition border-b border-gray-800 last:border-0">
                <td class="px-6 py-4 font-bold text-white text-lg">${item.ticker}</td>
                <td class="px-6 py-4 text-center text-gray-300 font-mono">${item.total_predictions}</td>
                <td class="px-6 py-4 text-center font-bold ${colorClass} text-lg">${item.accuracy}%</td>
                <td class="px-6 py-4 text-center text-blue-300 font-mono">± ${item.avg_error}%</td>
            </tr>
            `;
      })
      .join("");
  } catch (e) {
    console.error("Erro no loadStats:", e);
    const tbody = document.getElementById("statsTable");
    if (tbody)
      tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-4 text-center text-red-500">Erro de conexão com o servidor.</td></tr>`;
  }
}

// ======================================================
// 2. CARREGA O LOG DETALHADO (Com Indicadores)
// ======================================================
async function loadLog() {
  try {
    const res = await fetch(`${API_BASE}/history/log`);

    if (!res.ok) throw new Error("Erro ao buscar histórico");

    const data = await res.json();
    const tbody = document.getElementById("logTable");

    if (!tbody) return;

    if (data.length === 0) {
      tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="px-6 py-8 text-center text-gray-500">
                        Nenhuma pesquisa registrada ainda. <br>
                        <span class="text-xs">Faça uma análise no Laboratório para começar.</span>
                    </td>
                </tr>`;
      return;
    }

    tbody.innerHTML = data
      .map((item) => {
        // 1. Formata Indicadores (Separa a string por vírgula e cria spans)
        const rawIndicators = item.indicators || "Padrão";
        const indicatorsHtml = rawIndicators
          .split(", ")
          .map(
            (ind) =>
              `<span class="inline-block bg-gray-700 text-gray-300 px-2 py-0.5 rounded text-[10px] mr-1 mb-1 border border-gray-600 font-mono">${ind}</span>`
          )
          .join("");

        // 2. Formata Preços
        const predPrice = item.predicted
          ? `R$ ${item.predicted.toFixed(2)}`
          : "--";
        const realPrice = item.real
          ? `R$ ${item.real.toFixed(2)}`
          : '<span class="text-gray-600">--</span>';

        // 3. Ícone de Status
        let statusIcon = '<span class="text-gray-500 text-xs">⏳</span>';
        if (item.result && item.result.includes("✅"))
          statusIcon = '<span class="text-green-500 text-lg">✅</span>';
        if (item.result && item.result.includes("❌"))
          statusIcon = '<span class="text-red-500 text-lg">❌</span>';

        return `
            <tr class="hover:bg-gray-700 transition border-b border-gray-800 last:border-0">
                <td class="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">${item.date}</td>
                <td class="px-4 py-3 text-gray-200 font-bold text-xs whitespace-nowrap">${item.target_date}</td>
                <td class="px-4 py-3 text-white font-bold text-sm">${item.ticker}</td>
                <td class="px-4 py-3 align-middle leading-none">${indicatorsHtml}</td>
                <td class="px-4 py-3 text-right text-blue-300 font-mono text-sm">${predPrice}</td>
                <td class="px-4 py-3 text-right text-yellow-300 font-mono text-sm">${realPrice}</td>
                <td class="px-4 py-3 text-center">${statusIcon}</td>
            </tr>
            `;
      })
      .join("");
  } catch (e) {
    console.error("Erro no loadLog:", e);
    const tbody = document.getElementById("logTable");
    if (tbody)
      tbody.innerHTML = `<tr><td colspan="7" class="px-6 py-4 text-center text-red-500">Erro ao carregar o log.</td></tr>`;
  }
}

// Inicia o carregamento assim que o script é lido
loadData();
