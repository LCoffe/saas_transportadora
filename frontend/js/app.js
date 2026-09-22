// Atualiza a interface dinâmica de acordo com o perfil logado
function atualizarInterface() {
    const token = getToken();
    const loginSection = document.getElementById("login-section");
    const dashboardSection = document.getElementById("dashboard-section");
    const userInfo = document.getElementById("user-info");

    const userRole = localStorage.getItem("user_tipo") || "CLIENTE";
    const userEmail = localStorage.getItem("user_email") || "Utilizador";

    if (token) {
        loginSection.classList.add("hidden");
        dashboardSection.classList.remove("hidden");
        userInfo.classList.remove("hidden");
        
        document.getElementById("user-name").innerText = userEmail;
        document.getElementById("user-role").innerText = `Perfil: ${userRole}`;

        // Elementos de controlo de permissão na tela
        const cadastroPanel = document.getElementById("cadastro-usuario-panel");
        const motoristaPanel = document.getElementById("motorista-panel");
        const optFuncionario = document.getElementById("opt-funcionario");
        const optAdmin = document.getElementById("opt-admin");

        // Regras de exibição por perfil
        if (userRole === "ADMIN") {
            cadastroPanel.classList.remove("hidden");
            motoristaPanel.classList.remove("hidden");
            
            // ADMIN pode cadastrar qualquer perfil
            optFuncionario.disabled = false;
            optFuncionario.classList.remove("hidden");
            optAdmin.disabled = false;
            optAdmin.classList.remove("hidden");
            
            document.getElementById("titulo-cadastro-usuario").innerText = "Gestão Global de Utilizadores (Admin)";
        } 
        else if (userRole === "FUNCIONARIO") {
            cadastroPanel.classList.remove("hidden");
            motoristaPanel.classList.add("hidden"); // Central não envia comandos diretos
            
            // FUNCIONARIO só pode cadastrar CLIENTE (Caminhoneiros)
            optFuncionario.disabled = true;
            optFuncionario.classList.add("hidden");
            optAdmin.disabled = true;
            optAdmin.classList.add("hidden");
            
            document.getElementById("new-user-tipo").value = "CLIENTE";
            document.getElementById("titulo-cadastro-usuario").innerText = "Registro de Motoristas / Caminhoneiros";
        } 
        else { // CLIENTE (Motorista)
            cadastroPanel.classList.add("hidden");
            motoristaPanel.classList.remove("hidden");
        }

        carregarComandos();
        carregarHistoricoComandos();
    } else {
        loginSection.classList.remove("hidden");
        dashboardSection.classList.add("hidden");
        userInfo.classList.add("hidden");
    }
}

// Submissão do formulário de Login simplificado (apenas E-mail e Senha)
async function handleLogin(event) {
    event.preventDefault();
    
    const inputUsuario = document.getElementById("login-email").value.trim().toLowerCase();
    const senhaDigitada = document.getElementById("login-password").value.trim();
    const errorElement = document.getElementById("login-error");

    errorElement.classList.add("hidden");

    try {
        const response = await fetch(`${API_URL}/usuarios/`);
        
        if (!response.ok) {
            throw new Error("Erro ao ligar ao servidor.");
        }

        const usuarios = await response.json();
        
        // Procura o utilizador correspondente pelo e-mail ou nome
        const usuarioValido = usuarios.find(u => 
            u.email.toLowerCase() === inputUsuario || 
            u.nome.toLowerCase() === inputUsuario
        );

        // Como o esquema oculta a senha da listagem pública, validamos a presença do utilizador
        if (usuarioValido && senhaDigitada.length > 0) {
            setToken("token-demo-saas-123");
            localStorage.setItem("user_id", usuarioValido.id);
            localStorage.setItem("user_email", usuarioValido.email);
            localStorage.setItem("user_tipo", usuarioValido.tipo);

            atualizarInterface();
        } else {
            errorElement.innerText = "E-mail ou utilizador não encontrado.";
            errorElement.classList.remove("hidden");
        }
    } catch (err) {
        console.error("Erro no login:", err);
        errorElement.innerText = "Falha ao ligar à API. Verifique se o backend está em execução.";
        errorElement.classList.remove("hidden");
    }
}

// Encerra a sessão
function logout() {
    removeToken();
    localStorage.removeItem("user_id");
    localStorage.removeItem("user_email");
    localStorage.removeItem("user_tipo");
    atualizarInterface();
}

// Executa o registo de utilizador enviando o criador_id
async function cadastrarUsuario(event) {
    event.preventDefault();

    const nome = document.getElementById("new-user-name").value;
    const email = document.getElementById("new-user-email").value;
    const senha = document.getElementById("new-user-password").value;
    const tipo = document.getElementById("new-user-tipo").value;
    
    const criadorId = localStorage.getItem("user_id") || 1;

    try {
        const response = await apiFetch(`/usuarios/?criador_id=${criadorId}`, {
            method: "POST",
            body: JSON.stringify({ nome, email, senha, tipo })
        });

        if (response.ok) {
            alert(`Utilizador (${tipo}) registado com sucesso!`);
            document.getElementById("user-create-form").reset();
        } else {
            const errData = await response.json();
            alert(`Erro no registo: ${errData.detail || 'Verifique as permissões do seu perfil.'}`);
        }
    } catch (err) {
        console.error("Erro ao registar utilizador:", err);
    }
}

// Motorista solicita envio de comando ao veículo
async function solicitarComando(event) {
    event.preventDefault();
    const veiculoId = parseInt(document.getElementById("cmd-veiculo-id").value);
    const tipoComando = document.getElementById("cmd-tipo").value;
    const motoristaId = localStorage.getItem("user_id") || 1;

    try {
        const response = await apiFetch(`/comandos/solicitar?motorista_id=${motoristaId}`, {
            method: "POST",
            body: JSON.stringify({
                veiculo_id: veiculoId,
                tipo_comando: tipoComando
            })
        });

        if (response.ok) {
            alert("Solicitação enviada à central com sucesso!");
            carregarComandos();
        } else {
            const errData = await response.json();
            alert(`Erro na solicitação: ${errData.detail || 'Verifique se o veículo pertence ao seu utilizador.'}`);
        }
    } catch (err) {
        console.error("Erro ao solicitar comando:", err);
    }
}

// Lista os comandos de telemetria
async function carregarComandos() {
    const tableBody = document.getElementById("commands-table-body");
    tableBody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-500">A carregar dados de telemetria...</td></tr>`;

    try {
        const response = await apiFetch("/comandos/pendentes");
        if (!response.ok) throw new Error("Erro ao carregar lista de comandos.");

        const comandos = await response.json();
        const userRole = localStorage.getItem("user_tipo");

        if (comandos.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-500">Nenhuma solicitação na fila.</td></tr>`;
            return;
        }

        tableBody.innerHTML = comandos.map(cmd => `
            <tr class="border-b border-slate-700/50 hover:bg-slate-800/50 transition">
                <td class="p-3 font-mono text-slate-400">#${cmd.id}</td>
                <td class="p-3 font-semibold text-slate-200">Veículo #${cmd.veiculo_id}</td>
                <td class="p-3 text-slate-300">Motorista #${cmd.solicitado_por_id}</td>
                <td class="p-3 font-mono text-amber-400">${cmd.tipo_comando}</td>
                <td class="p-3">
                    <span class="px-2 py-1 text-xs rounded font-medium ${
                        cmd.status === 'PENDENTE' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                        cmd.status === 'APROVADO' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                        'bg-red-500/10 text-red-400 border border-red-500/20'
                    }">
                        ${cmd.status}
                    </span>
                </td>
                <td class="p-3">
                    ${(cmd.status === 'PENDENTE' && (userRole === 'FUNCIONARIO' || userRole === 'ADMIN')) ? `
                        <button onclick="analisarComando(${cmd.id}, 'APROVADO')" class="bg-emerald-600 hover:bg-emerald-700 text-white text-xs px-2.5 py-1 rounded mr-1 transition">Aprovar</button>
                        <button onclick="analisarComando(${cmd.id}, 'REJEITADO')" class="bg-red-600 hover:bg-red-700 text-white text-xs px-2.5 py-1 rounded transition">Rejeitar</button>
                    ` : `<span class="text-xs text-slate-500">${cmd.status === 'PENDENTE' ? 'Aguardando Central' : 'Finalizado'}</span>`}
                </td>
            </tr>
        `).join('');

    } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-red-400">Erro ao atualizar telemetria.</td></tr>`;
    }
}

// Carrega o histórico das últimas 5 interações concluídas
async function carregarHistoricoComandos() {
    const tableBody = document.getElementById("history-table-body");
    if (!tableBody) return;

    tableBody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-slate-500">A carregar histórico...</td></tr>`;

    try {
        const response = await apiFetch("/comandos/historico");
        if (!response.ok) throw new Error("Erro ao carregar histórico.");

        const historico = await response.json();

        if (historico.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-slate-500">Nenhum comando finalizado no histórico.</td></tr>`;
            return;
        }

        tableBody.innerHTML = historico.map(cmd => `
            <tr class="border-b border-slate-700/50 hover:bg-slate-800/50 transition">
                <td class="p-3 font-mono text-slate-400">#${cmd.id}</td>
                <td class="p-3 font-semibold text-slate-200">Veículo #${cmd.veiculo_id}</td>
                <td class="p-3 font-mono text-amber-400">${cmd.tipo_comando}</td>
                <td class="p-3">
                    <span class="px-2 py-1 text-xs rounded font-medium ${
                        cmd.status === 'APROVADO' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                        'bg-red-500/10 text-red-400 border border-red-500/20'
                    }">
                        ${cmd.status}
                    </span>
                </td>
                <td class="p-3 text-xs text-slate-400">
                    ${cmd.observacao || 'Sem observações'}
                </td>
            </tr>
        `).join('');

    } catch (err) {
        console.error("Erro ao carregar histórico:", err);
        tableBody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-red-400">Erro ao carregar dados do histórico.</td></tr>`;
    }
}

// Analisa e responde a um comando (Apenas Central/Admin)
async function analisarComando(comandoId, novoStatus) {
    const funcionarioId = localStorage.getItem("user_id") || 2;

    try {
        const response = await apiFetch(`/comandos/${comandoId}/analisar?funcionario_id=${funcionarioId}`, {
            method: "PATCH",
            body: JSON.stringify({
                status: novoStatus,
                observacao: `Ação (${novoStatus}) realizada em ${new Date().toLocaleTimeString()}`
            })
        });

        if (response.ok) {
            carregarComandos(); // Atualiza a fila
            carregarHistoricoComandos(); // Atualiza a tabela de histórico
        } else {
            const errData = await response.json();
            alert(`Erro na análise: ${errData.detail || 'Sem permissão.'}`);
        }
    } catch (err) {
        console.error("Erro ao analisar comando:", err);
    }
}
// Inicialização da página
document.addEventListener("DOMContentLoaded", atualizarInterface);
