// Função auxiliar para chamadas HTTP
async function apiFetch(endpoint, options = {}) {
    const token = getToken();
    const headers = {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers
    };

    return fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers
    });
}

// Controla a visibilidade dos campos do veículo no formulário
function toggleCamposVeiculo() {
    const elTipo = document.getElementById("new-user-tipo");
    const boxVeiculo = document.getElementById("box-veiculo");
    if (boxVeiculo && elTipo) {
        boxVeiculo.style.display = (elTipo.value === "CLIENTE") ? "grid" : "none";
    }
}

// Função responsável por alternar entre a tela de Login e o Painel Principal
function atualizarInterface() {
    const token = localStorage.getItem("access_token") || localStorage.getItem("user_email");
    const loginSection = document.getElementById("secao-login");
    const appSection = document.getElementById("secao-app");

    if (!loginSection || !appSection) {
        console.error("IDs 'secao-login' ou 'secao-app' não foram encontrados no HTML.");
        return;
    }

    // SE ESTIVER LOGADO:
    if (token) {
        loginSection.classList.add("hidden");   // Esconde formulário de login
        appSection.classList.remove("hidden"); // Mostra a aplicação

        // Busca o nome e o tipo salvos no localStorage
        const nome = localStorage.getItem("user_nome") || localStorage.getItem("user_email") || "Usuário";
        const tipo = localStorage.getItem("user_tipo") || "CLIENTE";

        const nameElement = document.getElementById("user-display-name");
        const typeElement = document.getElementById("user-display-role");

        if (nameElement) nameElement.innerText = nome;
        if (typeElement) typeElement.innerText = `[${tipo}]`;
        
        // Aplica as regras de RBAC por tipo de perfil (CLIENTE, FUNCIONARIO, ADMIN)
        aplicarPermissoesPerfil();
        carregarListaUsuariosEdicao();
    } 
    // SE NÃO ESTIVER LOGADO:
    else {
        loginSection.classList.remove("hidden"); // Mostra login
        appSection.classList.add("hidden");     // Esconde aplicação
    }
}

// Controla quais blocos cada perfil pode ver dentro da aplicação
function aplicarPermissoesPerfil() {
    const userTipo = localStorage.getItem("user_tipo") || "CLIENTE";

    const painelMotorista = document.getElementById("painel-motorista");
    const painelGestao = document.getElementById("painel-gestao");
    const optFuncionario = document.getElementById("opt-funcionario");
    const optAdmin = document.getElementById("opt-admin");
    const selectTipo = document.getElementById("new-user-tipo");

    // Oculta ambos os painéis por padrão
    if (painelMotorista) painelMotorista.classList.add("hidden");
    if (painelGestao) painelGestao.classList.add("hidden");

    // Exibe o painel adequado conforme o tipo de conta
    if (userTipo === "CLIENTE") {
        if (painelMotorista) painelMotorista.classList.remove("hidden");
    } else if (userTipo === "FUNCIONARIO" || userTipo === "ADMIN") {
        if (painelGestao) painelGestao.classList.remove("hidden");
    }

    // Regra RBAC para opções de criação de perfil
    if (userTipo === "FUNCIONARIO") {
        // Funcionário só pode cadastrar CLIENTE (Motorista)
        if (optFuncionario) optFuncionario.style.display = "none";
        if (optAdmin) optAdmin.style.display = "none";
        if (selectTipo) selectTipo.value = "CLIENTE";
    } else if (userTipo === "ADMIN") {
        // Administrador tem acesso total a todos os perfis
        if (optFuncionario) optFuncionario.style.display = "block";
        if (optAdmin) optAdmin.style.display = "block";
    }

    // Atualiza a exibição dos campos de veículo conforme o perfil selecionado
    toggleCamposVeiculo();
}

// Submissão do formulário de Login
async function handleLogin(event) {
    event.preventDefault();
    
    const loginInput = document.getElementById("login-email").value.trim().toLowerCase();
    const senhaDigitada = document.getElementById("login-password").value.trim();
    const errorElement = document.getElementById("login-error");

    if (errorElement) errorElement.classList.add("hidden");

    try {
        const response = await fetch(`${API_URL}/usuarios/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ 
                login: loginInput, 
                senha: senhaDigitada 
            })
        });

        if (!response.ok) {
            const erroData = await response.json();
            localStorage.clear();

            if (errorElement) {
                errorElement.innerText = erroData.detail || "E-mail/Utilizador ou senha incorretos.";
                errorElement.classList.remove("hidden");
            }
            return; 
        }

        const usuario = await response.json();

        localStorage.setItem("access_token", usuario.access_token);
        localStorage.setItem("user_id", usuario.usuario_id);
        localStorage.setItem("user_nome", usuario.nome);
        localStorage.setItem("user_email", usuario.email);
        localStorage.setItem("user_tipo", usuario.tipo);

        atualizarInterface();

    } catch (err) {
        console.error("Erro no login:", err);
        localStorage.clear();
        if (errorElement) {
            errorElement.innerText = "Erro ao conectar com o servidor de autenticação.";
            errorElement.classList.remove("hidden");
        }
    }
}

// Encerra a sessão
function handleLogout() {
    removeToken();
    localStorage.clear();
    atualizarInterface();
}

// Executa o registro de usuário enviando o criador_id
async function cadastrarUsuario(event) {
    event.preventDefault();

    const getVal = (id) => {
        const el = document.getElementById(id);
        return el ? el.value.trim() : "";
    };

    const nome = getVal("new-user-nome");
    const email = getVal("new-user-email");
    const senha = getVal("new-user-senha");
    const tipo = getVal("new-user-tipo");
    const userTipoLogado = localStorage.getItem("user_tipo");

    // Validação de segurança no front-end para o perfil FUNCIONARIO
    if (userTipoLogado === "FUNCIONARIO" && (tipo === "FUNCIONARIO" || tipo === "ADMIN")) {
        alert("Permissão negada: Funcionários só podem cadastrar usuários do tipo Motorista/Cliente.");
        return;
    }
    
    const criadorId = localStorage.getItem("user_id") || 1;
    const payload = { nome, email, senha, tipo };

    if (tipo && tipo.toUpperCase() === "CLIENTE") {
        const veiculoModelo = getVal("new-veiculo-modelo");
        const veiculoPlaca = getVal("new-veiculo-placa");
        const veiculoMarca = getVal("new-veiculo-marca") || null;
        const anoInput = getVal("new-veiculo-ano");
        const veiculoAno = anoInput ? parseInt(anoInput) : null;

        if (!veiculoPlaca || !veiculoModelo) {
            alert("Para registrar um motorista, é obrigatório informar o modelo e a placa do veículo.");
            return;
        }
        payload.veiculo = { placa: veiculoPlaca, modelo: veiculoModelo, marca: veiculoMarca, ano: veiculoAno };
    }

    try {
        const response = await apiFetch(`/usuarios/?criador_id=${criadorId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload })
        });

        if (response.ok) {
            alert(`Usuário (${tipo}) registrado com sucesso!`);
            const form = document.getElementById("user-create-form");
            if (form) form.reset();
            
            // Reaplica as permissões para redefinir as opções do select e os campos do veículo
            aplicarPermissoesPerfil();
        } else {
            const errData = await response.json();
            alert(`Erro no registro: ${errData.detail || 'Verifique os dados.'}`);
        }
    } catch (err) {
        console.error("Erro ao registrar usuário:", err);
    }
}

// Carrega a lista de usuários respeitando o perfil logado
async function carregarListaUsuariosEdicao() {
    const userTipo = localStorage.getItem("user_tipo");
    const userId = localStorage.getItem("user_id");

    try {
        const response = await apiFetch(`/usuarios/?usuario_logado_id=${userId}&usuario_logado_tipo=${userTipo}`);
        
        if (!response.ok) {
            console.error("Erro ao buscar utilizadores:", response.status);
            return;
        }

        const usuarios = await response.json();
        console.log("Lista de usuários carregada:", usuarios);
        console.log("Veiculo associado:", usuarios.veiculo);
        const tbody = document.getElementById("tbody-gerenciar-usuarios");
        const template = document.getElementById("template-usuario-linha"); // Pega o template do HTML

        if (!tbody || !template) return;

        tbody.innerHTML = "";

        if (!usuarios || usuarios.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="p-4 text-center text-slate-500 italic">
                        Nenhum utilizador encontrado.
                    </td>
                </tr>`;
            return;
        }

        usuarios.forEach(u => {
            if (userTipo === "CLIENTE" && u.id != userId) return;
            if (userTipo === "FUNCIONARIO" && u.tipo !== "CLIENTE" && u.id != userId) return;

            // Clona a estrutura HTML do template
            const clone = template.content.cloneNode(true);

            // Preenche os textos
            clone.querySelector(".col-id").textContent = `#${u.id}`;
            clone.querySelector(".col-nome").textContent = u.nome;
            clone.querySelector(".col-email").textContent = u.email;
            clone.querySelector(".col-tipo").textContent = u.tipo;

            // Configura o botão de Editar dinamicamente
            const btnEditar = clone.querySelector(".btn-editar");
            btnEditar.onclick = () => abrirModalEdicao(u.id, u.tipo);

            // Configura o botão de Excluir dinamicamente
            const btnExcluir = clone.querySelector(".btn-excluir");
            btnExcluir.onclick = () => excluirCadastroUsuario(u.id);

            // Adiciona a linha pronta na tabela
            tbody.appendChild(clone);
        });
    } catch (err) {
        console.error("Erro ao carregar utilizadores para edição:", err);
    }
}

// Função para excluir utilizador diretamente pela tabela
async function excluirCadastroUsuario(id) {
    if (!confirm("Tem a certeza de que deseja excluir este utilizador?")) return;

    const logadoId = localStorage.getItem("user_id");
    const logadoTipo = localStorage.getItem("user_tipo");

    try {
        const response = await apiFetch(`/usuarios/${id}?usuario_logado_id=${logadoId}&usuario_logado_tipo=${logadoTipo}`, {
            method: "DELETE"
        });

        if (response.status === 204 || response.ok) {
            alert("Utilizador excluído com sucesso!");
            carregarListaUsuariosEdicao();
        } else {
            const err = await response.json();
            alert(`Erro ao excluir: ${err.detail || 'Permissão negada.'}`);
        }
    } catch (error) {
        console.error("Erro na requisição de exclusão:", error);
    }
}

    async function abrirModalEdicao(id, nomeAtual, emailAtual, tipoAtual) {
        console.log("--- INÍCIO DA EDIÇÃO ---");
        console.log("1. tipoAtual recebido no parâmetro:", tipoAtual);

        const logadoId = localStorage.getItem("user_id");
        const logadoTipo = localStorage.getItem("user_tipo");

        document.getElementById("modalUserId").value = id;
        document.getElementById("modalSenha").value = "";

        try {
            const response = await fetch(`/usuarios/${id}?usuario_logado_id=${logadoId}&usuario_logado_tipo=${logadoTipo}`);
            
            if (response.ok) {
                const usuario = await response.json();
                console.log("2. Objeto completo retornado pela API:", usuario);
                console.log("3. usuario.tipo vindo do banco:", usuario.tipo);
                
                document.getElementById("modalNome").value = usuario.nome || "";
                document.getElementById("modalEmail").value = usuario.email || "";

                // Vamos priorizar o tipo que vem do banco (usuario.tipo), ou o parâmetro se não houver
                const tipoBruto = usuario.tipo || tipoAtual || "";
                const tipoFormatado = tipoBruto.toUpperCase();
                
                console.log("4. Tipo formatado para comparação:", tipoFormatado);

                if (tipoFormatado === "CLIENTE") {
                    console.log(">>> SUCESSO: Entrou no IF de CLIENTE! <<<");
                    
                    document.getElementById("blocoVeiculo").style.display = "block";
                    
                    if (usuario.veiculo) {
                        console.log("5. Veículo encontrado:", usuario.veiculo);
                        document.getElementById("modalPlaca").value = usuario.veiculo.placa || "";
                        document.getElementById("modalModelo").value = usuario.veiculo.modelo || "";
                        document.getElementById("modalMarca").value = usuario.veiculo.marca || "";
                        document.getElementById("modalAno").value = usuario.veiculo.ano || "";
                    } else {
                        console.log("5. Aviso: O usuário é cliente, mas veio sem veículo cadastrado.");
                        document.getElementById("modalPlaca").value = "";
                        document.getElementById("modalModelo").value = "";
                        document.getElementById("modalMarca").value = "";
                        document.getElementById("modalAno").value = "";
                    }
                } else {
                    console.log(">>> ATENÇÃO: Caiu no ELSE (Não reconheceu como CLIENTE) <<<");
                    document.getElementById("blocoVeiculo").style.display = "none";
                }

                document.getElementById("modalEdicao").style.display = "flex";

            } else {
                alert("Não foi possível carregar os dados do utilizador.");
            }
        } catch (error) {
            console.error("Erro ao buscar utilizador:", error);
        }
    }

    function fecharModalEdicao() {
        document.getElementById("modalEdicao").style.display = "none";
    }

// 3. Salva as alterações via PUT
async function salvarEdicaoModal(event) {
    event.preventDefault();

    const id = document.getElementById("modalUserId").value;
    const novoNome = document.getElementById("modalNome").value;
    const novoEmail = document.getElementById("modalEmail").value;
    const novaSenha = document.getElementById("modalSenha").value;

    const payload = {
        nome: novoNome,
        email: novoEmail
    };

    if (novaSenha && novaSenha.trim() !== "") {
        payload.senha = novaSenha.trim();
    }

    const logadoId = localStorage.getItem("user_id");
    const logadoTipo = localStorage.getItem("user_tipo");
    if (logadoTipo == "CLIENTE"){
        // Se for CLIENTE, também envia os dados do veículo
        payload.veiculo = {
            placa: document.getElementById("modalPlaca").value,
            modelo: document.getElementById("modalModelo").value,
            marca: document.getElementById("modalMarca").value,
            ano: parseInt(document.getElementById("modalAno").value) || null
        };
    }

    try {
        const response = await fetch(`/usuarios/${id}?usuario_logado_id=${logadoId}&usuario_logado_tipo=${logadoTipo}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            alert("Usuário atualizado com sucesso!");
            fecharModalEdicao(); // Fecha o modal
            carregarListaUsuariosEdicao(); // Atualiza a tabela na tela principal
        } else {
            const err = await response.json();
            alert(`Erro ao atualizar: ${err.detail || 'Permissão negada.'}`);
        }
    } catch (error) {
        console.error("Erro na requisição de atualização:", error);
    }
}

// Motorista solicita envio de comando ao veículo
async function solicitarComando(event) {
    event.preventDefault();

    const tipoComando = document.getElementById("cmd-tipo").value;
    const motoristaId = localStorage.getItem("user_id");

    if(!motoristaId){
        alert("Erro: ID do motorista não encontrado. Faça login novamente.");
        return;
    }

    try {
        const response = await apiFetch(`/comandos/solicitar?motorista_id=${motoristaId}`, {
            method: "POST",
            body: JSON.stringify({
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
    try {
        const userId = localStorage.getItem("user_id");
        const userTipo = localStorage.getItem("user_tipo");

        let url = "/comandos/";
        if (userId && userTipo && userTipo !== "null" && userTipo !== "undefined") {
            url += `?usuario_id=${encodeURIComponent(userId)}&tipo_usuario=${encodeURIComponent(userTipo.toUpperCase())}`;
        }

        const response = await apiFetch(url);
        if (!response.ok) return;

        const comandos = await response.json();
        const tbody = document.getElementById("tbody-comandos");
        if (!tbody) return;

        tbody.innerHTML = "";

        if (comandos.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="p-4 text-center text-slate-500 italic">
                        Nenhuma solicitação de comando encontrada na fila.
                    </td>
                </tr>`;
            return;
        }

        comandos.forEach(cmd => {
            const placaVeiculo = cmd.veiculo ? cmd.veiculo.placa : `Veículo #${cmd.veiculo_id}`;
            const nomeSolicitante = cmd.motorista ? cmd.motorista.nome : `Motorista #${cmd.motorista_id}`;

            const tr = document.createElement("tr");
            tr.className = "border-b border-slate-700/50 hover:bg-slate-800/50 transition";

            tr.innerHTML = `
                <td class="p-3 font-mono text-slate-400">#${cmd.id}</td>
                <td class="p-3 font-semibold text-white font-mono">${placaVeiculo}</td>
                <td class="p-3 text-slate-300 font-medium">${nomeSolicitante}</td>
                <td class="p-3 font-mono text-amber-400 font-bold">${cmd.tipo_comando}</td>
                <td class="p-3">
                    <span class="px-2 py-1 text-xs rounded font-bold ${getStatusBadgeClass(cmd.status)}">
                        ${cmd.status}
                    </span>
                </td>
                <td class="p-3">
                    ${getAcoesCentralHTML(cmd)}
                </td>
            `;

            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Erro ao carregar fila de comandos:", err);
    }
}

// Carrega o histórico das últimas 5 interações concluídas
async function carregarHistoricoDecisoes() {
    try {
        const userId = localStorage.getItem("user_id");
        const userTipo = localStorage.getItem("user_tipo");

        let url = "/comandos/historico";
        if (userId && userTipo && userTipo !== "null" && userTipo !== "undefined") {
            url += `?usuario_id=${encodeURIComponent(userId)}&tipo_usuario=${encodeURIComponent(userTipo.toUpperCase())}`;
        }

        const response = await apiFetch(url);
        if (!response.ok) return;

        const historico = await response.json();
        const tbody = document.getElementById("tbody-historico");
        if (!tbody) return;

        tbody.innerHTML = "";

        if (!historico || historico.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="p-4 text-center text-slate-500 italic">
                        Nenhum registro encontrado no histórico.
                    </td>
                </tr>`;
            return;
        }

        historico.forEach(cmd => {
            const placaVeiculo = cmd.veiculo ? cmd.veiculo.placa : `Veículo #${cmd.veiculo_id}`;
            const nomeSolicitante = cmd.motorista ? cmd.motorista.nome : `Motorista #${cmd.motorista_id}`;

            const tr = document.createElement("tr");
            tr.className = "border-b border-slate-700/50 hover:bg-slate-800/50 transition";

            tr.innerHTML = `
                <td class="p-3 font-mono text-slate-400">#${cmd.id}</td>
                <td class="p-3 font-semibold text-white font-mono">${placaVeiculo}</td>
                <td class="p-3 text-slate-300 font-medium">${nomeSolicitante}</td>
                <td class="p-3 font-mono text-amber-400 font-bold">${cmd.tipo_comando}</td>
                <td class="p-3">
                    <span class="px-2 py-1 text-xs rounded font-bold ${getStatusBadgeClass(cmd.status)}">
                        ${cmd.status}
                    </span>
                </td>
                <td class="p-3 text-xs text-slate-400 italic">
                    ${cmd.observacao || 'Sem observações cadastradas'}
                </td>
            `;

            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Erro ao renderizar histórico de decisões:", err);
    }
}

// Auxiliares para badges e botões de ação
function getStatusBadgeClass(status) {
    switch (status) {
        case 'PENDENTE': return 'bg-amber-500/20 text-amber-400 border border-amber-500/30';
        case 'APROVADO': return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
        case 'REJEITADO': return 'bg-rose-500/20 text-rose-400 border border-rose-500/30';
        case 'EXECUTADO': return 'bg-blue-500/20 text-blue-400 border border-blue-500/30';
        default: return 'bg-slate-700 text-slate-300';
    }
}

function getAcoesCentralHTML(cmd) {
    const userTipo = localStorage.getItem("user_tipo");

    if (cmd.status === 'PENDENTE' && (userTipo === 'FUNCIONARIO' || userTipo === 'ADMIN')) {
        return `
            <div class="flex gap-2">
                <button onclick="analisarComando(${cmd.id}, 'APROVADO')" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-2.5 py-1 rounded transition">
                    Aprovar
                </button>
                <button onclick="analisarComando(${cmd.id}, 'REJEITADO')" class="bg-rose-600 hover:bg-rose-500 text-white text-xs px-2.5 py-1 rounded transition">
                    Rejeitar
                </button>
            </div>
        `;
    }

    return `<span class="text-xs text-slate-500 italic">Aguardando Central</span>`;
}

// Analisa e responde a um comando (Central/Admin)
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
            carregarComandos();
            carregarHistoricoDecisoes();
        } else {
            const errData = await response.json();
            alert(`Erro na análise: ${errData.detail || 'Sem permissão.'}`);
        }
    } catch (err) {
        console.error("Erro ao analisar comando:", err);
    }
}

// Alterna os painéis colapsáveis (Accordion)
function togglePainel(containerId, setaId, funcaoCarregar = null) {
    const container = document.getElementById(containerId);
    const seta = document.getElementById(setaId);

    if (!container) return;

    const estaOculto = container.classList.contains("hidden");

    if (estaOculto) {
        container.classList.remove("hidden");
        if (seta) seta.classList.add("rotate-180");

        if (typeof funcaoCarregar === "function") {
            funcaoCarregar();
        }
    } else {
        container.classList.add("hidden");
        if (seta) seta.classList.remove("rotate-180");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    atualizarInterface();
});