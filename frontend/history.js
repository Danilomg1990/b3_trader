// history.js

const API_URL = "http://127.0.0.1:8000/history/stats";

async function loadData() {
  await loadStats();
  await loadLog();
}

// 1. Carrega o Resumo (Ranking)
async function loadStats() {
  try {
    const res = await fetch(`${API_BASE}/history/stats`);
    const data = await res.json();
    const tbody = document.getElementById("statsTable");

    if (data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-4 text-center text-gray-500">Sem dados auditados ainda.</td></tr>`;
      return;
    }

    tbody.innerHTML = data
      .map(
        (item) => `
            <tr class="hover:bg-gray-700 transition">
                <td class="px-6 py-3 font-bold text-white">${item.ticker}</td>
                <td class="px-6 py-3 text-center text-gray-300">${
                  item.total_predictions
                }</td>
                <td class="px-6 py-3 text-center font-bold ${
                  item.accuracy >= 50 ? "text-green-400" : "text-red-400"
                }">${item.accuracy}%</td>
                <td class="px-6 py-3 text-center text-blue-300">± ${
                  item.avg_error
                }%</td>
            </tr>
        `
      )
      .join("");
  } catch (e) {
    console.error(e);
  }
}

// 2. Carrega o Log Detalhado (Com Indicadores)
async function loadLog() {
  try {
    const res = await fetch(`${API_BASE}/history/log`);
    const data = await res.json();
    const tbody = document.getElementById("logTable");

    if (data.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="px-6 py-4 text-center text-gray-500">Nenhuma pesquisa registrada.</td></tr>`;
      return;
    }

    tbody.innerHTML = data
      .map((item) => {
        // Formata os indicadores para ficar bonito (tags)
        const indicatorsHtml = item.indicators
          .split(", ")
          .map(
            (ind) =>
              `<span class="inline-block bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded text-[10px] mr-1 mb-1 border border-gray-600">${ind}</span>`
          )
          .join("");

        return `
            <tr class="hover:bg-gray-700 transition">
                <td class="px-4 py-3 text-gray-400">${item.date}</td>
                <td class="px-4 py-3 text-gray-300 font-bold">${
                  item.target_date
                }</td>
                <td class="px-4 py-3 text-white font-bold">${item.ticker}</td>
                <td class="px-4 py-3">${indicatorsHtml}</td>
                <td class="px-4 py-3 text-right text-blue-300">R$ ${item.predicted.toFixed(
                  2
                )}</td>
                <td class="px-4 py-3 text-right text-yellow-300">${
                  item.real ? "R$ " + item.real.toFixed(2) : "--"
                }</td>
                <td class="px-4 py-3 text-center">${item.result}</td>
            </tr>
            `;
      })
      .join("");
  } catch (e) {
    console.error(e);
  }
}
// Executa assim que o script carrega
loadStats();
